"""
Agent API routes for managing AI assistants (digital humans).
"""
import re
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.deps import get_current_user
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentStatusUpdate,
    AgentResponse,
    AgentDetail,
    AgentListResponse,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetail,
    ConversationListResponse,
    MessageCreate,
    MessageResponse,
    TrainingTaskCreate,
    TrainingTaskResponse,
    TrainingTaskListResponse,
    ChatRequest,
    ChatResponse,
    AgentStatus,
    TrainingStatus,
    AgentNameSuggestionRequest,
    AgentNameSuggestionResponse,
)
from app.services.langchain_glm_service import langchain_glm_service
from app.models.user import User
from app.models.agent import Agent, Conversation, Message, TrainingTask

router = APIRouter()


# ==================== AI Name Suggestion ====================

# Domain labels mapping
DOMAIN_LABELS = {
    'code': '代码开发',
    'writing': '内容写作',
    'analysis': '数据分析',
    'design': '设计创意',
    'translation': '翻译',
    'general': '通用助手',
}


@router.post("/suggest-name", response_model=AgentNameSuggestionResponse)
async def suggest_agent_name(
    request: AgentNameSuggestionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate AI-powered agent name suggestions based on domain.
    """
    # Get domain label
    domain_label = DOMAIN_LABELS.get(request.domain, request.domain)

    # Build prompt for GLM
    system_prompt = """你是一个创意命名专家，专门为AI智能体起名字。
请根据用户提供的领域，生成5个有创意、专业且好记的智能体名称。
命名要求：
1. 名称要简洁有力，2-6个中文字符
2. 体现该领域的专业特点
3. 带有一定的科技感和未来感
4. 容易记忆和发音

请只返回名称列表，每行一个名称，不要加序号或其他内容。"""

    user_prompt = f"请为{domain_label}领域的AI智能体推荐5个名称"
    if request.description:
        user_prompt += f"，额外描述：{request.description}"

    try:
        # Call GLM service
        response = await langchain_glm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,  # Higher temperature for more creativity
            max_tokens=200,
        )

        # Parse response into list of names
        names = [
            line.strip()
            for line in response.strip().split('\n')
            if line.strip() and not line.strip().startswith(('1', '2', '3', '4', '5', '-', '*', '•'))
        ]

        # Clean up any remaining numbering
        clean_names = []
        for name in names[:5]:  # Take max 5 names
            # Remove common prefixes
            clean_name = name.lstrip('0123456789.、-: ')
            if clean_name:
                clean_names.append(clean_name)

        # Fallback if no names extracted
        if not clean_names:
            clean_names = [f"{domain_label}助手", f"智能{domain_label}专家", f"{domain_label}大师"]

        return AgentNameSuggestionResponse(
            names=clean_names[:5],
            domain=request.domain,
        )

    except Exception as e:
        # Fallback on error
        return AgentNameSuggestionResponse(
            names=[f"{domain_label}助手", f"智能{domain_label}专家", f"{domain_label}AI"],
            domain=request.domain,
        )


# ==================== Agent CRUD ====================

@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new agent (digital human) for the current user.
    """
    new_agent = Agent(
        user_id=current_user.id,
        name=agent_data.name,
        description=agent_data.description,
        domain=agent_data.domain,
        system_prompt=agent_data.system_prompt,
        config=agent_data.config or {},
        status=AgentStatus.draft,
    )

    db.add(new_agent)
    await db.commit()
    await db.refresh(new_agent)

    return AgentResponse(
        id=new_agent.id,
        user_id=new_agent.user_id,
        name=new_agent.name,
        description=new_agent.description,
        domain=new_agent.domain,
        avatar_url=new_agent.avatar_url,
        status=new_agent.status.value,
        conversation_count=0,
        created_at=new_agent.created_at,
        updated_at=new_agent.updated_at,
    )


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all agents for the current user with pagination and filtering.
    """
    # Build base query
    base_filters = [Agent.user_id == current_user.id]

    if status_filter:
        try:
            status_enum = AgentStatus(status_filter)
            base_filters.append(Agent.status == status_enum)
        except ValueError:
            pass
    if domain:
        base_filters.append(Agent.domain == domain)
    if search:
        base_filters.append(
            or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%"),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(Agent).where(*base_filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get agents
    offset = (page - 1) * page_size
    agents_query = (
        select(Agent)
        .where(*base_filters)
        .order_by(Agent.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(agents_query)
    agents = result.scalars().all()

    # Build response with conversation counts
    agent_responses = []
    for agent in agents:
        # Count conversations
        conv_count_query = select(func.count()).select_from(Conversation).where(
            Conversation.agent_id == agent.id
        )
        conv_count_result = await db.execute(conv_count_query)
        conversation_count = conv_count_result.scalar() or 0

        agent_responses.append(
            AgentResponse(
                id=agent.id,
                user_id=agent.user_id,
                name=agent.name,
                description=agent.description,
                domain=agent.domain,
                avatar_url=agent.avatar_url,
                status=agent.status.value,
                conversation_count=conversation_count,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return AgentListResponse(
        items=agent_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific agent by ID with detailed information.
    """
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Count conversations
    conv_count_query = select(func.count()).select_from(Conversation).where(
        Conversation.agent_id == agent.id
    )
    conv_count_result = await db.execute(conv_count_query)
    conversation_count = conv_count_result.scalar() or 0

    return AgentDetail(
        id=agent.id,
        user_id=agent.user_id,
        name=agent.name,
        description=agent.description,
        domain=agent.domain,
        avatar_url=agent.avatar_url,
        status=agent.status.value,
        system_prompt=agent.system_prompt,
        config=agent.config,
        conversation_count=conversation_count,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an agent's information.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update fields
    update_data = agent_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)

    # Count conversations
    conv_count_query = select(func.count()).select_from(Conversation).where(
        Conversation.agent_id == agent.id
    )
    conv_count_result = await db.execute(conv_count_query)
    conversation_count = conv_count_result.scalar() or 0

    return AgentResponse(
        id=agent.id,
        user_id=agent.user_id,
        name=agent.name,
        description=agent.description,
        domain=agent.domain,
        avatar_url=agent.avatar_url,
        status=agent.status.value,
        conversation_count=conversation_count,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.patch("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: int,
    status_update: AgentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an agent's status.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    agent.status = status_update.status
    await db.commit()
    await db.refresh(agent)

    # Count conversations
    conv_count_query = select(func.count()).select_from(Conversation).where(
        Conversation.agent_id == agent.id
    )
    conv_count_result = await db.execute(conv_count_query)
    conversation_count = conv_count_result.scalar() or 0

    return AgentResponse(
        id=agent.id,
        user_id=agent.user_id,
        name=agent.name,
        description=agent.description,
        domain=agent.domain,
        avatar_url=agent.avatar_url,
        status=agent.status.value,
        conversation_count=conversation_count,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an agent and all its conversations.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    await db.execute(delete(Agent).where(Agent.id == agent_id))
    await db.commit()


# ==================== Conversation Management ====================

@router.get("/{agent_id}/conversations", response_model=ConversationListResponse)
async def list_agent_conversations(
    agent_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all conversations for a specific agent.
    """
    # Verify agent ownership
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Get total count
    count_query = select(func.count()).select_from(Conversation).where(
        Conversation.agent_id == agent_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get conversations
    offset = (page - 1) * page_size
    conv_query = (
        select(Conversation)
        .where(Conversation.agent_id == agent_id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(conv_query)
    conversations = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return ConversationListResponse(
        items=[ConversationResponse.model_validate(c) for c in conversations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ==================== Conversation Endpoints ====================

conversations_router = APIRouter()


@conversations_router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conv_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new conversation with an agent.
    """
    # Verify agent ownership
    agent_result = await db.execute(select(Agent).where(Agent.id == conv_data.agent_id))
    agent = agent_result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    new_conversation = Conversation(
        agent_id=conv_data.agent_id,
        user_id=current_user.id,
        title=conv_data.title,
        summary=conv_data.summary,
        message_count=0,
    )

    db.add(new_conversation)
    await db.commit()
    await db.refresh(new_conversation)

    return ConversationDetail(
        id=new_conversation.id,
        agent_id=new_conversation.agent_id,
        user_id=new_conversation.user_id,
        title=new_conversation.title,
        summary=new_conversation.summary,
        message_count=new_conversation.message_count,
        created_at=new_conversation.created_at,
        updated_at=new_conversation.updated_at,
        messages=[],
    )


@conversations_router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a conversation with all its messages.
    """
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return ConversationDetail(
        id=conversation.id,
        agent_id=conversation.agent_id,
        user_id=conversation.user_id,
        title=conversation.title,
        summary=conversation.summary,
        message_count=conversation.message_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(m) for m in conversation.messages],
    )


@conversations_router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a conversation and all its messages.
    """
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await db.execute(delete(Conversation).where(Conversation.id == conversation_id))
    await db.commit()


# ==================== Training Task Endpoints ====================

training_router = APIRouter()


@training_router.post("", response_model=TrainingTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_training_task(
    task_data: TrainingTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new training task for an agent.
    """
    # Verify agent ownership
    agent_result = await db.execute(select(Agent).where(Agent.id == task_data.agent_id))
    agent = agent_result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    new_task = TrainingTask(
        agent_id=task_data.agent_id,
        user_id=current_user.id,
        name=task_data.name,
        description=task_data.description,
        training_data=task_data.training_data,
        config=task_data.config,
        status=TrainingStatus.pending,
        progress=0,
    )

    # Update agent status to training
    agent.status = AgentStatus.training

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    return TrainingTaskResponse.model_validate(new_task)


@training_router.get("", response_model=TrainingTaskListResponse)
async def list_training_tasks(
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all training tasks for the current user.
    """
    base_filters = [TrainingTask.user_id == current_user.id]
    if agent_id:
        base_filters.append(TrainingTask.agent_id == agent_id)

    # Get total count
    count_query = select(func.count()).select_from(TrainingTask).where(*base_filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get tasks
    offset = (page - 1) * page_size
    tasks_query = (
        select(TrainingTask)
        .where(*base_filters)
        .order_by(TrainingTask.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(tasks_query)
    tasks = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return TrainingTaskListResponse(
        items=[TrainingTaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@training_router.get("/{task_id}", response_model=TrainingTaskResponse)
async def get_training_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific training task.
    """
    result = await db.execute(select(TrainingTask).where(TrainingTask.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return TrainingTaskResponse.model_validate(task)
