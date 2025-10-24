from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field, EmailStr

from sfera_hack.connetors.sfera import get_sfera_client

router = APIRouter()


# UserSuggestion model based on swagger definition
class UserSuggestion(BaseModel):
    """Represents the suggestion user"""
    
    email: Optional[EmailStr] = Field(None, description="Unique primary email")
    first_name: Optional[str] = Field(None, description="First name", alias="firstName")
    full_name: Optional[str] = Field(None, description="Full name", alias="fullName")
    last_name: Optional[str] = Field(None, description="Last name", alias="lastName")
    login: Optional[str] = Field(None, description="User login")
    middle_name: Optional[str] = Field(None, description="Middle name", alias="middleName")
    principal_name: Optional[str] = Field(None, description="User principal name", alias="principalName")
    
    model_config = {"populate_by_name": True}


# Page metadata for paginated responses
class ResponsePageMeta(BaseModel):
    """Page metadata for paginated responses"""
    
    cursor: Optional[str] = Field(None, description="Cursor for next page")
    limit: int = Field(..., description="Page size")
    total: Optional[int] = Field(None, description="Total number of items")


# Response model for user suggestions
class UserSuggestionsResponse(BaseModel):
    """Response model for user suggestions"""
    
    data: List[UserSuggestion] = Field(..., description="List of user suggestions")
    page: ResponsePageMeta = Field(..., description="Page metadata")


# Error response model
class ErrorResponse(BaseModel):
    """Error response model"""
    
    error: str
    message: str
    request_id: Optional[str] = None


def get_auth_token(request: Request) -> str:
    """Get authentication token from cookies"""
    access_token = request.cookies.get("ACCESS_TOKEN")
    if not access_token:
        raise HTTPException(
            status_code=401, detail="Authentication required. Please login first."
        )
    return access_token


@router.get(
    "/projects/{project_key}/repos/{repo_name}/pull-requests/user-suggestions",
    response_model=UserSuggestionsResponse,
)
async def get_user_suggestions(
    project_key: str,
    repo_name: str,
    request: Request,
    q: Optional[str] = Query(
        None,
        description="Filter by name or email",
    ),
    pr_id: Optional[int] = Query(
        None,
        description="Pull request id",
        alias="prId",
    ),
    skip_self: Optional[bool] = Query(
        None,
        description="Skip current user from response",
        alias="skipSelf",
    ),
    cursor: Optional[str] = Query(
        None,
        description="Cursor of the requested page (received from the previous request)",
    ),
    limit: Optional[int] = Query(
        30,
        description="Page size of results",
    ),
):
    """
    Get user suggestions for specified pull request.
    Returns user suggestions with pagination metadata.
    """
    try:
        # Validate limit
        if limit and (limit < 1 or limit > 5000):
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 5000"
            )
        
        # Get authentication token from cookies
        access_token = get_auth_token(request)
        
        # Prepare query parameters
        params = {}
        
        if q:
            params["q"] = q
        if pr_id:
            params["prId"] = pr_id
        if skip_self is not None:
            params["skipSelf"] = skip_self
        if cursor:
            params["cursor"] = cursor
        if limit:
            params["limit"] = limit
        
        # Use Sfera API client to get user suggestions
        sfera_client = await get_sfera_client(access_token)
        response = await sfera_client.get_user_suggestions(project_key, repo_name, params)
        
        # Transform the response
        users_data = response.get("data", [])
        users = []
        
        for user_data in users_data:
            user = UserSuggestion(
                email=user_data.get("email"),
                firstName=user_data.get("first_name"),
                fullName=user_data.get("full_name"),
                lastName=user_data.get("last_name"),
                login=user_data.get("login"),
                middleName=user_data.get("middle_name"),
                principalName=user_data.get("principal_name"),
            )
            users.append(user)
        
        # Create page metadata
        page_data = response.get("page", {})
        page_meta = ResponsePageMeta(
            cursor=page_data.get("cursor"),
            limit=page_data.get("limit", limit or 30),
            total=page_data.get("total"),
        )
        
        return UserSuggestionsResponse(
            data=users,
            page=page_meta,
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
