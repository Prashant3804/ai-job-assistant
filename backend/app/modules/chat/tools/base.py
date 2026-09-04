import asyncio
import time
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, List
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("chat_tools")

class ToolResult(BaseModel):
    tool_name: str
    success: bool
    summary: str
    data: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0

class BaseTool(ABC):
    name: str
    description: str
    category: str  # "RESUME", "JOB", "MATCHING", "APPLICATION"
    parameters_schema: Type[BaseModel]

    @abstractmethod
    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: BaseModel) -> ToolResult:
        """Execute the tool with authenticated user identity and database session."""
        pass

    async def execute(self, user_id: uuid.UUID, db: AsyncSession, raw_args: Dict[str, Any], timeout_seconds: float = 5.0) -> ToolResult:
        start_time = time.time()
        try:
            # Validate arguments strictly against Pydantic schema
            validated_params = self.parameters_schema.model_validate(raw_args or {})
        except ValidationError as val_err:
            dur = round((time.time() - start_time) * 1000, 2)
            logger.warning(f"Tool {self.name} argument validation failed: {val_err}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                summary=f"Invalid arguments for {self.name}: {val_err.errors()[0].get('msg', 'validation error')}",
                error=str(val_err),
                duration_ms=dur
            )

        try:
            result = await asyncio.wait_for(
                self.run(user_id=user_id, db=db, params=validated_params),
                timeout=timeout_seconds
            )
            result.duration_ms = round((time.time() - start_time) * 1000, 2)
            return result
        except asyncio.TimeoutError:
            dur = round((time.time() - start_time) * 1000, 2)
            logger.error(f"Tool {self.name} timed out after {timeout_seconds}s")
            return ToolResult(
                tool_name=self.name,
                success=False,
                summary=f"Tool {self.name} execution timed out.",
                error="TIMEOUT",
                duration_ms=dur
            )
        except Exception as exc:
            dur = round((time.time() - start_time) * 1000, 2)
            logger.exception(f"Tool {self.name} failed with error: {exc}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                summary=f"Failed to execute {self.name}: {str(exc)}",
                error=str(exc),
                duration_ms=dur
            )

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.info(f"Registered chatbot tool: {tool.name} (category: {tool.category})")

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tool specifications."""
        definitions = []
        for tool in self._tools.values():
            schema = tool.parameters_schema.model_json_schema()
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema
                }
            })
        return definitions

    async def execute_tool(
        self,
        name: str,
        user_id: uuid.UUID,
        db: AsyncSession,
        arguments: Dict[str, Any],
        timeout_seconds: float = 5.0
    ) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                success=False,
                summary=f"Tool '{name}' is not recognized or permitted.",
                error="TOOL_NOT_FOUND",
                duration_ms=0.0
            )
        return await tool.execute(user_id=user_id, db=db, raw_args=arguments, timeout_seconds=timeout_seconds)
