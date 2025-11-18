from typing import Optional
from core.redis_client import RedisCache
from models.user import User


# Cache TTL configurations
USER_CACHE_TTL = 300  # 5 minutes
SESSION_CACHE_TTL = 3600  # 1 hour


class UserCacheService:
    """Service for caching user data"""
    
    @staticmethod
    def _get_user_key(user_id: int) -> str:
        """Generate cache key for user"""
        return f"user:{user_id}"
    
    @staticmethod
    async def get_user(user_id: int) -> Optional[dict]:
        """Get user from cache"""
        key = UserCacheService._get_user_key(user_id)
        return await RedisCache.get(key)  # Add await
    
    @staticmethod
    async def set_user(user: User, ttl: int = USER_CACHE_TTL):
        """Cache user data"""
        key = UserCacheService._get_user_key(user.id)
        user_dict = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "is_active": user.is_active
        }
        await RedisCache.set(key, user_dict, ttl)  # Add await
    
    @staticmethod
    async def invalidate_user(user_id: int):
        """Remove user from cache"""
        key = UserCacheService._get_user_key(user_id)
        await RedisCache.delete(key)  # Add await
    
    @staticmethod
    async def invalidate_all_users():
        """Clear all user caches"""
        await RedisCache.clear_pattern("user:*")  # Add await


class CacheService:
    """Generic cache service for any model"""
    
    @staticmethod
    async def get(model_name: str, item_id: int) -> Optional[dict]:
        """Get any model from cache"""
        key = f"{model_name}:{item_id}"
        return await RedisCache.get(key)  # Add await
    
    @staticmethod
    async def set(model_name: str, item_id: int, data: dict, ttl: int = 300):
        """Cache any model"""
        key = f"{model_name}:{item_id}"
        await RedisCache.set(key, data, ttl)  # Add await
    
    @staticmethod
    async def invalidate(model_name: str, item_id: int):
        """Invalidate any model cache"""
        key = f"{model_name}:{item_id}"
        await RedisCache.delete(key)  # Add await
    
    @staticmethod
    async def invalidate_list(model_name: str):
        """Invalidate all list caches for a model"""
        await RedisCache.clear_pattern(f"{model_name}:list:*")  # Add await


# Usage example for teams
class TeamCacheService:
    """Service for caching team data"""
    
    TEAM_CACHE_TTL = 300  # 5 minutes
    
    @staticmethod
    async def get_team(team_id: int) -> Optional[dict]:
        """Get team from cache"""
        return await CacheService.get("team", team_id)  # Add await
    
    @staticmethod
    async def set_team(team_id: int, team_data: dict, ttl: int = TEAM_CACHE_TTL):
        """Cache team data"""
        await CacheService.set("team", team_id, team_data, ttl)  # Add await
    
    @staticmethod
    async def invalidate_team(team_id: int):
        """Invalidate team cache"""
        await CacheService.invalidate("team", team_id)  # Add await
    
    @staticmethod
    async def invalidate_all_teams():
        """Invalidate all team caches"""
        await RedisCache.clear_pattern("team:*")  # Add await


# Usage example for projects
class ProjectCacheService:
    """Service for caching project data"""
    
    PROJECT_CACHE_TTL = 300  # 5 minutes
    
    @staticmethod
    async def get_project(project_id: int) -> Optional[dict]:
        """Get project from cache"""
        return await CacheService.get("project", project_id)
    
    @staticmethod
    async def set_project(project_id: int, project_data: dict, ttl: int = PROJECT_CACHE_TTL):
        """Cache project data"""
        await CacheService.set("project", project_id, project_data, ttl)
    
    @staticmethod
    async def invalidate_project(project_id: int):
        """Invalidate project cache"""
        await CacheService.invalidate("project", project_id)
    
    @staticmethod
    async def invalidate_all_projects():
        """Invalidate all project caches"""
        await RedisCache.clear_pattern("project:*")


# Usage example for tasks
class TaskCacheService:
    """Service for caching task data"""
    
    TASK_CACHE_TTL = 180  # 3 minutes (tasks change more frequently)
    
    @staticmethod
    async def get_task(task_id: int) -> Optional[dict]:
        """Get task from cache"""
        return await CacheService.get("task", task_id)
    
    @staticmethod
    async def set_task(task_id: int, task_data: dict, ttl: int = TASK_CACHE_TTL):
        """Cache task data"""
        await CacheService.set("task", task_id, task_data, ttl)
    
    @staticmethod
    async def invalidate_task(task_id: int):
        """Invalidate task cache"""
        await CacheService.invalidate("task", task_id)
    
    @staticmethod
    async def invalidate_all_tasks():
        """Invalidate all task caches"""
        await RedisCache.clear_pattern("task:*")
    
    @staticmethod
    async def invalidate_project_tasks(project_id: int):
        """Invalidate all tasks for a specific project"""
        await RedisCache.clear_pattern(f"task:project:{project_id}:*")
