import asyncio
import os
from typing import List
import uuid

from fastapi import Depends, UploadFile
from mimetypes import guess_extension, guess_type

from app.services.user_onboarding_service import UserOnboardingService
from app.routing.contracts.user_contracts import UpdateProfilePayload
from common.storage import StoragePurpose, get_bucket, get_public_object_url, object_exists
from domain.schema.user import User, UserIdentifiers, UserIncludes, UserProfile
from domain.schema.profile import (
    UserProfileFrontend,
    UserProfileBackend,
    UserProfileDatabase,
    UserProfileDevops,
    UserProfileHobby,
    UserProfileStudent,
    UserProfileProfessional
)
from app.repositories.user_repository import UserRepository

class UserCreationError(Exception):
    def __repr__(self):
        return "User creation failed"

class UserService:
    """
    Handles primary business logic associated with user accounts on the platform.
    
    Attributes:
        user_repo (UserRepository): The repository for user data
    """
    
    onboarding_service: UserOnboardingService
    user_repo: UserRepository
    
    def __init__(self, user_onboarding_service: UserOnboardingService = Depends(UserOnboardingService), user_repo: UserRepository = Depends(UserRepository)):
        self.onboarding_service = user_onboarding_service
        self.user_repo = user_repo

    async def create_user(self, email_address: str, username: str, password_hash: str) -> User:
        """
        Creates a new user and profile

        Args:
            email_address (str): The user's email address
            username (str): The unique name for the user
            password_hash (str): A hash derived from the user's password

        Raises:
            UserCreationError: Email or username already in use

        Returns:
            User: The newly created user
        """
        existing_email, existing_username = await asyncio.gather(
            self.user_repo.get_user("email", email_address),
            self.user_repo.get_user("username", username)
        )
        
        if existing_email:
            raise UserCreationError("Email already in use")
        
        if existing_username:
            raise UserCreationError("Username already in use")
        
        # Create the user record
        user = await self.user_repo.create_user(email_address, username, password_hash)
        
        # Begin onboarding with verification
        await self.onboarding_service.send_verification_email(user.id)
        
        return user
    
    async def get_user(self, by: UserIdentifiers, value: str, include: List[UserIncludes] = ["profile"]) -> User:
        """
        Retrieves a user by one of their unique identifiers, optionally providing related data.
        Profiles are included by default.

        Args:
            by (UserIdentifiers): The type of identifier to search by
            value (str): The value of the identifier
            include (List[UserIncludes], optional): Which related entities to populate. Defaults to ["profile"].

        Raises:
            ValueError: User not found

        Returns:
            User: The user record
        """
        user = await self.user_repo.get_user(by, value, include)
        
        if user is None:
            raise ValueError("User not found")
        
        return user
    
    async def update_profile(self, user_id: str, profile_dto: UpdateProfilePayload):
        """
        Updates a user's profile with the provided data.

        Args:
            user_id (str): The ID of the user to update
            profile (UpdateProfilePayload): The new profile data

        Raises:
            ValueError: User not found
            ValueError: Invalid file was supplied for avatar
        """
        user = await self.get_user("id", user_id, ["profile"])
        
        if user is None:
            raise ValueError("User not found")
        
        user.profile.first_name = profile_dto.first_name
        user.profile.last_name = profile_dto.last_name
        user.profile.bio = profile_dto.bio
        user.profile.github_username = profile_dto.github_username
        
        # If they provided a file id, check if it exists and get the URL for it
        if profile_dto.avatar_file_id is not None:
            bucket = get_bucket(StoragePurpose.AVATAR)
            bucket_id = self._get_avatar_bucket_id(user_id, profile_dto.avatar_file_id)
            
            if not object_exists(bucket, bucket_id):
                raise ValueError("Invalid file")
            
            user.profile.avatar_url = get_public_object_url(StoragePurpose.AVATAR, bucket_id)
        else:
            user.profile.avatar_url = user.profile.avatar_url # Keep the existing avatar if none was provided
        
        if profile_dto.learning_capacities:
            if "hobby" in profile_dto.learning_capacities:
                if profile_dto.hobby:
                    #user.profile.hobby
                    pass
                else:
                    user.profile.hobby = UserProfileHobby(user_profile_id=user.profile.id)
            elif user.profile.hobby is not None:
                user.profile.hobby = None
                
            if "student" in profile_dto.learning_capacities:
                user.profile.student = UserProfileStudent(user_profile_id=user.profile.id)
            else:
                user.profile.student = None
                
            if "professional" in profile_dto.learning_capacities:
                user.profile.professional = UserProfileProfessional(user_profile_id=user.profile.id)
            else:
                user.profile.professional = None
                
        if profile_dto.disciplines:
            if "frontend" in profile_dto.disciplines:
                user.profile.frontend = UserProfileFrontend(user_profile_id=user.profile.id)
            elif user.profile.frontend is not None:
                user.profile.frontend = None
                
            if "backend" in profile_dto.disciplines:
                user.profile.backend = UserProfileBackend(user_profile_id=user.profile.id)
            elif user.profile.backend is not None:
                user.profile.backend = None
                
            if "database" in profile_dto.disciplines:
                user.profile.database = UserProfileDatabase(user_profile_id=user.profile.id)
            elif user.profile.database is not None:
                user.profile.database = None
                
            if "devops" in profile_dto.disciplines:
                user.profile.devops = UserProfileDevops(user_profile_id=user.profile.id)
            elif user.profile.devops is not None:
                user.profile.devops = None
        
        await self.user_repo.upsert_profile(
            user_id=user.id, 
            profile=user.profile
        )
        
    async def upload_avatar(self, user_id: str, file: UploadFile) -> str:
        """
        Handles the upload of an avatar file for a given user to supply during profile updates.

        Args:
            user_id (str): The ID of the user to upload the avatar for
            file (UploadFile): The file to upload

        Raises:
            ValueError: User not found

        Returns:
            str: The object ID of the uploaded file in the storage bucket
        """
        user = await self.get_user("id", user_id)
        
        if user is None:
            raise ValueError("User not found")
        
        # Get the S3 bucket
        bucket = get_bucket(StoragePurpose.AVATAR)
        
        # Parse out mimetype and extension
        mimetype, _ = guess_type(file.filename)
        extension = os.path.splitext(file.filename)[1] if not mimetype else guess_extension(mimetype)
        
        # Create the object and bucket IDs
        object_id = uuid.uuid4().hex + extension
        bucket_id = self._get_avatar_bucket_id(user_id, object_id)
        
        # Upload the file
        bucket.put_object(Key=bucket_id, Body=await file.read(), ContentType=mimetype, ACL="public-read")
        
        return object_id
    
    def _get_avatar_bucket_id(self, user_id: str, object_id: str) -> str:
        """
        Helper function to generate the avatar bucket ID for a specific user

        Args:
            user_id (str): The user ID
            object_id (str): The object ID

        Returns:
            str: A bucket ID
        """
        return f"{user_id}/{object_id}"