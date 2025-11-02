"""
Usage tracking and quota management for AIezzy.
Tracks API usage and enforces tier-based limits.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Optional
from models_v2 import db, User, UsageLog, DailyUsage
from config import get_config
from sqlalchemy import func

config = get_config()

class QuotaService:
    """Service for tracking usage and enforcing quotas"""

    # Tier limits (daily)
    TIER_LIMITS = {
        'free': {
            'images': config.QUOTA_FREE_IMAGES,
            'videos': config.QUOTA_FREE_VIDEOS,
            'messages': config.QUOTA_FREE_MESSAGES
        },
        'pro': {
            'images': config.QUOTA_PRO_IMAGES,
            'videos': config.QUOTA_PRO_VIDEOS,
            'messages': config.QUOTA_PRO_MESSAGES
        },
        'enterprise': {
            'images': 999999,  # Unlimited
            'videos': 999999,
            'messages': 999999
        },
        'guest': {
            'images': 5,  # Very limited for guests
            'videos': 2,
            'messages': 20
        }
    }

    def __init__(self):
        pass

    def log_usage(self, user_id: Optional[int], resource_type: str, count: int = 1, metadata: Dict = None) -> bool:
        """
        Log API usage for a user

        Args:
            user_id: User ID (None for guests)
            resource_type: Type of resource (image, video, message)
            count: Number of resources used
            metadata: Additional metadata (JSON)

        Returns:
            bool: True if logged successfully
        """
        try:
            # Create usage log entry
            usage_log = UsageLog(
                user_id=user_id if user_id else 0,  # 0 for guests
                resource_type=resource_type,
                resource_count=count,
                resource_metadata=str(metadata) if metadata else None
            )
            db.session.add(usage_log)

            # Update daily usage aggregate
            if user_id:
                today = date.today()
                daily_usage = DailyUsage.query.filter_by(
                    user_id=user_id,
                    date=today
                ).first()

                if not daily_usage:
                    daily_usage = DailyUsage(user_id=user_id, date=today)
                    db.session.add(daily_usage)

                # Increment appropriate counter
                if resource_type == 'image':
                    daily_usage.images_generated += count
                elif resource_type == 'video':
                    daily_usage.videos_created += count
                elif resource_type == 'message':
                    daily_usage.messages_sent += count

            db.session.commit()
            return True

        except Exception as e:
            print(f"Error logging usage: {e}")
            db.session.rollback()
            return False

    def get_daily_usage(self, user_id: Optional[int], resource_type: str, days: int = 1) -> int:
        """
        Get usage count for a resource type

        Args:
            user_id: User ID (None for guests)
            resource_type: Type of resource
            days: Number of days to look back (1 = today only)

        Returns:
            int: Total usage count
        """
        try:
            if not user_id:
                # For guests, use session-based tracking (not persistent)
                return 0

            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days - 1)

            # Query daily usage
            usage = db.session.query(
                func.sum(getattr(DailyUsage, f'{resource_type}s_generated' if resource_type == 'image'
                                 else f'{resource_type}s_created' if resource_type == 'video'
                                 else f'{resource_type}s_sent'))
            ).filter(
                DailyUsage.user_id == user_id,
                DailyUsage.date >= start_date,
                DailyUsage.date <= end_date
            ).scalar()

            return usage or 0

        except Exception as e:
            print(f"Error getting daily usage: {e}")
            return 0

    def check_quota(self, user_id: Optional[int], resource_type: str, requested_count: int = 1) -> Dict:
        """
        Check if user has quota available for resource

        Args:
            user_id: User ID (None for guests)
            resource_type: Type of resource
            requested_count: Number of resources requested

        Returns:
            dict: {
                'allowed': bool,
                'remaining': int,
                'limit': int,
                'tier': str,
                'message': str (if not allowed)
            }
        """
        # Get user tier
        if user_id:
            user = User.query.get(user_id)
            tier = user.tier if user else 'free'
        else:
            tier = 'guest'

        # Get tier limits
        limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS['free'])
        limit = limits.get(resource_type, 0)

        # Get current usage
        current_usage = self.get_daily_usage(user_id, resource_type, days=1)

        # Calculate remaining
        remaining = max(0, limit - current_usage)

        # Check if allowed
        allowed = remaining >= requested_count

        result = {
            'allowed': allowed,
            'remaining': remaining,
            'limit': limit,
            'tier': tier,
            'current_usage': current_usage
        }

        if not allowed:
            result['message'] = f"Daily {resource_type} limit reached ({limit}). Remaining: {remaining}. Upgrade to Pro for higher limits!"

        return result

    def get_user_quota_status(self, user_id: Optional[int]) -> Dict:
        """
        Get complete quota status for user across all resource types

        Args:
            user_id: User ID

        Returns:
            dict: Complete quota status
        """
        if not user_id:
            tier = 'guest'
        else:
            user = User.query.get(user_id)
            tier = user.tier if user else 'free'

        limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS['free'])

        status = {
            'tier': tier,
            'limits': limits,
            'usage': {},
            'remaining': {}
        }

        for resource_type in ['image', 'video', 'message']:
            usage = self.get_daily_usage(user_id, resource_type, days=1)
            limit = limits.get(f'{resource_type}s', limits.get(resource_type, 0))
            remaining = max(0, limit - usage)

            status['usage'][resource_type] = usage
            status['remaining'][resource_type] = remaining

        return status

    def reset_daily_usage(self, user_id: int) -> bool:
        """
        Reset daily usage for a user (admin function)

        Args:
            user_id: User ID

        Returns:
            bool: True if successful
        """
        try:
            today = date.today()
            daily_usage = DailyUsage.query.filter_by(
                user_id=user_id,
                date=today
            ).first()

            if daily_usage:
                daily_usage.images_generated = 0
                daily_usage.videos_created = 0
                daily_usage.messages_sent = 0
                db.session.commit()

            return True

        except Exception as e:
            print(f"Error resetting daily usage: {e}")
            db.session.rollback()
            return False

    def upgrade_user_tier(self, user_id: int, new_tier: str) -> bool:
        """
        Upgrade/downgrade user tier

        Args:
            user_id: User ID
            new_tier: New tier (free, pro, enterprise)

        Returns:
            bool: True if successful
        """
        try:
            if new_tier not in ['free', 'pro', 'enterprise']:
                return False

            user = User.query.get(user_id)
            if not user:
                return False

            user.tier = new_tier
            db.session.commit()
            return True

        except Exception as e:
            print(f"Error upgrading user tier: {e}")
            db.session.rollback()
            return False

    def get_usage_analytics(self, user_id: int, days: int = 30) -> Dict:
        """
        Get usage analytics for user over time period

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            dict: Usage analytics
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days - 1)

            # Get daily usage records
            daily_records = DailyUsage.query.filter(
                DailyUsage.user_id == user_id,
                DailyUsage.date >= start_date,
                DailyUsage.date <= end_date
            ).order_by(DailyUsage.date).all()

            # Calculate totals
            total_images = sum(r.images_generated for r in daily_records)
            total_videos = sum(r.videos_created for r in daily_records)
            total_messages = sum(r.messages_sent for r in daily_records)

            # Format daily breakdown
            daily_breakdown = [{
                'date': r.date.isoformat(),
                'images': r.images_generated,
                'videos': r.videos_created,
                'messages': r.messages_sent
            } for r in daily_records]

            return {
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'totals': {
                    'images': total_images,
                    'videos': total_videos,
                    'messages': total_messages
                },
                'daily': daily_breakdown
            }

        except Exception as e:
            print(f"Error getting usage analytics: {e}")
            return {'error': str(e)}

# Global quota service instance
quota_service = QuotaService()
