"""
Python Service Workflow Node Configuration - Clean Version
Uses proper Python enums without JavaScript-style patterns
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class InputType(str, Enum):
    """Input types for user input nodes"""
    DIGITS = "digits"
    SPEECH = "speech"
    BOTH = "both"

class NodeType(str, Enum):
    """Node types for workflow automation"""
    GREETING = "greeting"
    MENU = "menu"
    USER_INPUT = "input"
    SPEECH_INPUT = "speech_input"
    CONDITIONAL = "conditional"
    VOICEMAIL = "voicemail"
    TRANSFER = "transfer"
    REPEAT = "repeat"
    END = "end"
    AI_ASSISTANT = "ai_assistant"
    QUEUE = "queue"
    SMS = "sms"
    SET_VARIABLE = "set_variable"
    API_CALL = "api_call"

class NodeCategory(str, Enum):
    """Node categories"""
    INTERACTION = "interaction"
    LOGIC = "logic"
    ACTION = "action"
    SERVICE = "service"
    DATA = "data"

class OperatorType(str, Enum):
    """Operators for conditional nodes"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EXISTS = "exists"
    REGEX = "regex"

class CallDirection(str, Enum):
    """Call direction for transfer nodes"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class TransferMode(str, Enum):
    """Transfer modes"""
    BLIND = "blind"
    ATTENDED = "attended"

@dataclass
class NodeConfig:
    """Configuration for a workflow node"""
    node_type: NodeType
    name: str
    category: NodeCategory
    icon: str
    description: str
    color: str
    inputs: int
    outputs: List[str]
    data_schema: Dict[str, Any]
    validation: Optional[Dict[str, Any]] = None
    execution_config: Optional[Dict[str, Any]] = None

class NodeData(BaseModel):
    """Base class for node data"""
    class Config:
        extra = "allow"

class GreetingNodeData(NodeData):
    """Data structure for greeting/menu nodes"""
    text: str = Field(default="Welcome to our service.")
    voice: str = Field(default="alice", pattern="^(alice|man|woman|man|woman2)$")
    language: str = Field(default="en-US", pattern="^[a-z]{2}-[A-Z]{2}$")
    audio_url: Optional[str] = None
    menu_options: List[Dict[str, str]] = Field(default_factory=list)
    timeout: int = Field(default=10, ge=1, le=60)
    max_retries: int = Field(default=3, ge=1, le=10)

class UserInputNodeData(NodeData):
    """Data structure for user input nodes"""
    text: str = Field(default="Please enter your selection.")
    input_type: InputType = Field(default=InputType.DIGITS)
    num_digits: int = Field(default=1, ge=1, le=20)
    finish_on_key: str = Field(default="#", pattern="^(#|\\*|any|none)$")
    speech_timeout: int = Field(default=5, ge=1, le=30)
    speech_model: str = Field(default="default", pattern="^(default|phone_number|universal)$")
    timeout: int = Field(default=10, ge=1, le=60)
    max_retries: int = Field(default=3, ge=1, le=10)
    invalid_input_message: str = Field(default="Invalid input. Please try again.")
    validation: Optional[Dict[str, Any]] = None

class ConditionalNodeData(NodeData):
    """Data structure for conditional nodes"""
    variable: str = Field(default="caller_input")
    operator: OperatorType = Field(default=OperatorType.EQUALS)
    value: str = Field(..., min_length=1, max_length=200)
    custom_variable_name: Optional[str] = None
    case_sensitive: bool = Field(default=False)
    true_path_message: Optional[str] = None
    false_path_message: Optional[str] = None

class VoicemailNodeData(NodeData):
    """Data structure for voicemail nodes"""
    text: str = Field(default="Please leave your message after the beep.")
    max_length: int = Field(default=60, ge=1, le=300)
    transcribe: bool = Field(default=True)
    play_beep: bool = Field(default=True)
    recording_url: Optional[str] = None
    email_notifications: List[Dict[str, Any]] = Field(default_factory=list)
    silence_timeout: int = Field(default=5, ge=1, le=30)

class TransferNodeData(NodeData):
    """Data structure for transfer nodes"""
    destination: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    announce_text: Optional[str] = None
    timeout: int = Field(default=30, ge=1, le=120)
    caller_id: Optional[str] = None
    record: bool = Field(default=False)
    music_on_hold: str = Field(default="default", pattern="^(default|none|custom)$")
    custom_music_url: Optional[str] = None
    transfer_mode: TransferMode = Field(default=TransferMode.BLIND)

class RepeatNodeData(NodeData):
    """Data structure for repeat nodes"""
    max_repeats: int = Field(default=3, ge=1, le=10)
    repeat_message: Optional[str] = None
    fallback_node_id: Optional[str] = None
    fallback_message: Optional[str] = None
    replay_last_prompt: bool = Field(default=True)
    reset_on_repeat: bool = Field(default=False)

class EndNodeData(NodeData):
    """Data structure for end nodes"""
    text: Optional[str] = None
    reason: str = Field(default="normal", pattern="^(normal|error|timeout|hangup)$")
    log_data: bool = Field(default=True)
    send_summary: bool = Field(default=False)
    summary_email: Optional[str] = None

class AIAssistantNodeData(NodeData):
    """Data structure for AI assistant nodes"""
    stream_url: str = Field(..., pattern=r"^https?://[^\s/$]+")
    welcome_message: Optional[str] = None
    max_duration: int = Field(default=300, ge=30, le=1800)
    language: str = Field(default="en-US", pattern="^[a-z]{2}-[A-Z]{2}$")
    voice_profile: str = Field(default="professional", pattern="^(professional|friendly|casual)$")
    context_data: Optional[Dict[str, Any]] = None
    transfer_on_human_request: bool = Field(default=True)
    human_transfer_destination: Optional[str] = None

class QueueNodeData(NodeData):
    """Data structure for queue nodes"""
    queue_name: str = Field(default="General")
    max_wait_time: int = Field(default=300, ge=30, le=1800)
    wait_message: Optional[str] = None
    position_announcement: bool = Field(default=True)
    music_on_hold: str = Field(default="default", pattern="^(default|none|custom)$")
    custom_music_url: Optional[str] = None

class SMSNodeData(NodeData):
    """Data structure for SMS nodes"""
    message: str = Field(..., min_length=1, max_length=1600)
    to: Optional[str] = None
    from_number: Optional[str] = None
    send_immediately: bool = Field(default=True)

class SetVariableNodeData(NodeData):
    """Data structure for set variable nodes"""
    variable: str = Field(..., min_length=1, max_length=100)
    value: Union[str, int, float, bool, Dict[str, Any]]
    scope: str = Field(default="call", pattern="^(call|session|global)$")
    overwrite: bool = Field(default=True)

class APICallNodeData(NodeData):
    """Data structure for API call nodes"""
    url: str = Field(..., pattern=r"^https?://[^\s/$]+")
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|DELETE|PATCH)$")
    headers: Optional[Dict[str, str]] = None
    body: Optional[Union[str, Dict[str, Any]]] = None
    output_variable: Optional[str] = None
    timeout: int = Field(default=10, ge=1, le=60)
    retry_count: int = Field(default=0, ge=0, le=5)
    success_codes: List[int] = Field(default_factory=lambda: [200, 201, 202])

# Node configurations
NODE_CONFIGS = {
    NodeType.GREETING: NodeConfig(
        node_type=NodeType.GREETING,
        name="Greeting/Menu",
        category=NodeCategory.INTERACTION,
        icon="👋",
        description="Welcome message and menu options",
        color="#4CAF50",
        inputs=1,
        outputs=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "*", "#", "timeout", "no_match"],
        data_schema={
            "text": {"type": "string", "required": True},
            "voice": {"type": "select", "options": ["alice", "man", "woman", "man", "woman2"], "default": "alice"},
            "language": {"type": "string", "default": "en-US"},
            "audio_url": {"type": "string", "default": None},
            "menu_options": {"type": "array", "items": {"type": "object"}},
            "timeout": {"type": "number", "default": 10, "min": 1, "max": 60},
            "max_retries": {"type": "number", "default": 3, "min": 1, "max": 10}
        },
        execution_config={
            "auto_advance": False,
            "blocking": True,
            "collect_input": True
        }
    ),
    
    NodeType.USER_INPUT: NodeConfig(
        node_type=NodeType.USER_INPUT,
        name="User Input",
        category=NodeCategory.INTERACTION,
        icon="⌨️",
        description="Collect user input via DTMF or speech",
        color="#2196F3",
        inputs=1,
        outputs=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "*", "#", "timeout", "no_match"],
        data_schema={
            "text": {"type": "string", "required": True},
            "input_type": {"type": "select", "options": [InputType.DIGITS.value, InputType.SPEECH.value, InputType.BOTH.value], "default": InputType.DIGITS.value},
            "num_digits": {"type": "number", "default": 1, "min": 1, "max": 20},
            "timeout": {"type": "number", "default": 10, "min": 1, "max": 60},
            "max_retries": {"type": "number", "default": 3, "min": 1, "max": 10}
        },
        execution_config={
            "auto_advance": False,
            "blocking": True,
            "collect_input": True
        }
    ),
    
    NodeType.CONDITIONAL: NodeConfig(
        node_type=NodeType.CONDITIONAL,
        name="Conditional",
        category=NodeCategory.LOGIC,
        icon="🔀",
        description="Route calls based on conditions",
        color="#FF9800",
        inputs=1,
        outputs=["true", "false"],
        data_schema={
            "variable": {"type": "string", "required": True},
            "operator": {"type": "select", "options": [op.value for op in OperatorType], "default": OperatorType.EQUALS.value},
            "value": {"type": "string", "required": True},
            "case_sensitive": {"type": "boolean", "default": False}
        },
        execution_config={
            "auto_advance": True,
            "blocking": False,
            "collect_input": False
        }
    ),
    
    NodeType.VOICEMAIL: NodeConfig(
        node_type=NodeType.VOICEMAIL,
        name="Voicemail",
        category=NodeCategory.ACTION,
        icon="📬",
        description="Record voicemail messages",
        color="#9C27B0",
        inputs=1,
        outputs=["completed", "timeout", "error"],
        data_schema={
            "text": {"type": "string", "required": True},
            "max_length": {"type": "number", "default": 60, "min": 1, "max": 300},
            "transcribe": {"type": "boolean", "default": True},
            "play_beep": {"type": "boolean", "default": True}
        },
        execution_config={
            "auto_advance": False,
            "blocking": True,
            "collect_input": False
        }
    ),
    
    NodeType.TRANSFER: NodeConfig(
        node_type=NodeType.TRANSFER,
        name="Transfer",
        category=NodeCategory.ACTION,
        icon="📞",
        description="Transfer call to another number",
        color="#F44336",
        inputs=1,
        outputs=["answered", "busy", "no_answer", "failed"],
        data_schema={
            "destination": {"type": "string", "required": True},
            "announce_text": {"type": "string", "default": None},
            "timeout": {"type": "number", "default": 30, "min": 1, "max": 120}
        },
        execution_config={
            "auto_advance": False,
            "blocking": True,
            "collect_input": False
        }
    ),
    
    NodeType.REPEAT: NodeConfig(
        node_type=NodeType.REPEAT,
        name="Repeat",
        category=NodeCategory.LOGIC,
        icon="🔄",
        description="Repeat previous prompt or menu",
        color="#9E9E9E",
        inputs=1,
        outputs=["repeat", "fallback"],
        data_schema={
            "max_repeats": {"type": "number", "default": 3, "min": 1, "max": 10},
            "repeat_message": {"type": "string", "default": None},
            "fallback_node_id": {"type": "string", "default": None}
        },
        execution_config={
            "auto_advance": True,
            "blocking": False,
            "collect_input": False
        }
    ),
    
    NodeType.END: NodeConfig(
        node_type=NodeType.END,
        name="End",
        category=NodeCategory.ACTION,
        icon="🏁",
        description="End the call",
        color="#607D8B",
        inputs=1,
        outputs=[],
        data_schema={
            "text": {"type": "string", "default": None},
            "reason": {"type": "select", "options": ["normal", "error", "timeout", "hangup"], "default": "normal"}
        },
        execution_config={
            "auto_advance": False,
            "blocking": True,
            "collect_input": False
        }
    ),
    
    NodeType.AI_ASSISTANT: NodeConfig(
        node_type=NodeType.AI_ASSISTANT,
        name="AI Assistant",
        category=NodeCategory.SERVICE,
        icon="🤖",
        description="Connect to AI assistant",
        color="#673AB7",
        inputs=1,
        outputs=["completed", "transferred", "error"],
        data_schema={
            "stream_url": {"type": "string", "required": True},
            "welcome_message": {"type": "string", "default": None},
            "max_duration": {"type": "number", "default": 300, "min": 30, "max": 1800}
        },
        execution_config={
            "auto_advance": False,
            "blocking": True,
            "collect_input": False
        }
    )
}

class WorkflowNodeHandler:
    """Base class for handling workflow nodes"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def handle_node(self, node_type: NodeType, node_data: Dict[str, Any], 
                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a workflow node based on its type"""
        handler_method = getattr(self, f"handle_{node_type.value}", None)
        
        if handler_method:
            return await handler_method(node_data, context)
        else:
            self.logger.warning(f"No handler found for node type: {node_type}")
            return {
                "success": False,
                "error": f"Unknown node type: {node_type}",
                "action": "error"
            }
    
    async def handle_greeting(self, node_data: Dict[str, Any], 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle greeting/menu node"""
        text = node_data.get("text", "Welcome to our service.")
        
        # Generate prompt audio
        from core.pipeline import AIPipeline
        pipeline = AIPipeline()
        
        audio_result = await pipeline.tts.text_to_speech_bytes(text=text)
        
        return {
            "success": True,
            "action": "play_prompt",
            "prompt_audio": audio_result.get("audio_data"),
            "next_action": "wait_for_input"
        }
    
    async def handle_menu(self, node_data: Dict[str, Any], 
                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle menu node (similar to greeting)"""
        return await self.handle_greeting(node_data, context)
    
    async def handle_user_input(self, node_data: Dict[str, Any], 
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user input node"""
        text = node_data.get("text", "Please enter your selection.")
        input_type = node_data.get("input_type", InputType.DIGITS.value)
        
        # Generate prompt audio
        from core.pipeline import AIPipeline
        pipeline = AIPipeline()
        
        audio_result = await pipeline.tts.text_to_speech_bytes(text=text)
        
        return {
            "success": True,
            "action": "collect_input",
            "prompt_audio": audio_result.get("audio_data"),
            "input_type": input_type.value if isinstance(input_type, InputType) else input_type,
            "num_digits": node_data.get("num_digits", 1),
            "timeout": node_data.get("timeout", 10),
            "next_action": "wait_for_input"
        }
    
    async def handle_speech_input(self, node_data: Dict[str, Any], 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle speech input node"""
        return await self.handle_user_input(node_data, context)
    
    async def handle_conditional(self, node_data: Dict[str, Any], 
                              context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conditional node"""
        variable = node_data.get("variable", "caller_input")
        operator = node_data.get("operator", OperatorType.EQUALS.value)
        value = node_data.get("value", "")
        
        # Get actual value from context
        actual_value = context.get(variable)
        
        # Evaluate condition
        result = self.evaluate_condition(actual_value, operator, value)
        
        return {
            "success": True,
            "action": "evaluate_condition",
            "result": result,
            "next_action": "route_based_on_result"
        }
    
    async def handle_voicemail(self, node_data: Dict[str, Any], 
                              context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voicemail node"""
        text = node_data.get("text", "Please leave your message after the beep.")
        
        # Generate prompt audio
        from core.pipeline import AIPipeline
        pipeline = AIPipeline()
        
        audio_result = await pipeline.tts.text_to_speech_bytes(text=text)
        
        return {
            "success": True,
            "action": "record_voicemail",
            "prompt_audio": audio_result.get("audio_data"),
            "max_length": node_data.get("max_length", 60),
            "transcribe": node_data.get("transcribe", True),
            "next_action": "wait_for_recording"
        }
    
    async def handle_transfer(self, node_data: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transfer node"""
        destination = node_data.get("destination")
        announce_text = node_data.get("announce_text")
        
        # Generate announcement audio if provided
        prompt_audio = None
        if announce_text:
            from core.pipeline import AIPipeline
            pipeline = AIPipeline()
            audio_result = await pipeline.tts.text_to_speech_bytes(text=announce_text)
            prompt_audio = audio_result.get("audio_data")
        
        return {
            "success": True,
            "action": "transfer_call",
            "destination": destination,
            "prompt_audio": prompt_audio,
            "timeout": node_data.get("timeout", 30),
            "next_action": "initiate_transfer"
        }
    
    async def handle_repeat(self, node_data: Dict[str, Any], 
                         context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle repeat node"""
        repeat_message = node_data.get("repeat_message", "Repeating the options.")
        max_repeats = node_data.get("max_repeats", 3)
        
        # Generate repeat message audio
        from core.pipeline import AIPipeline
        pipeline = AIPipeline()
        
        audio_result = await pipeline.tts.text_to_speech_bytes(text=repeat_message)
        
        return {
            "success": True,
            "action": "repeat_prompt",
            "prompt_audio": audio_result.get("audio_data"),
            "max_repeats": max_repeats,
            "next_action": "repeat_or_fallback"
        }
    
    async def handle_end(self, node_data: Dict[str, Any], 
                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle end node"""
        text = node_data.get("text")
        reason = node_data.get("reason", "normal")
        
        # Generate end message audio if provided
        prompt_audio = None
        if text:
            from core.pipeline import AIPipeline
            pipeline = AIPipeline()
            audio_result = await pipeline.tts.text_to_speech_bytes(text=text)
            prompt_audio = audio_result.get("audio_data")
        
        return {
            "success": True,
            "action": "end_call",
            "prompt_audio": prompt_audio,
            "reason": reason,
            "next_action": "terminate_call"
        }
    
    async def handle_ai_assistant(self, node_data: Dict[str, Any], 
                                context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI assistant node"""
        stream_url = node_data.get("stream_url")
        welcome_message = node_data.get("welcome_message")
        
        # Generate welcome message audio if provided
        prompt_audio = None
        if welcome_message:
            from core.pipeline import AIPipeline
            pipeline = AIPipeline()
            audio_result = await pipeline.tts.text_to_speech_bytes(text=welcome_message)
            prompt_audio = audio_result.get("audio_data")
        
        return {
            "success": True,
            "action": "connect_ai_assistant",
            "stream_url": stream_url,
            "prompt_audio": prompt_audio,
            "max_duration": node_data.get("max_duration", 300),
            "next_action": "stream_to_ai"
        }
    
    def evaluate_condition(self, actual_value: Any, operator: str, expected_value: Any) -> bool:
        """Evaluate a condition based on operator"""
        try:
            if operator == OperatorType.EQUALS.value:
                return str(actual_value) == str(expected_value)
            elif operator == OperatorType.NOT_EQUALS.value:
                return str(actual_value) != str(expected_value)
            elif operator == OperatorType.CONTAINS.value:
                return str(expected_value) in str(actual_value)
            elif operator == OperatorType.GREATER_THAN.value:
                return float(actual_value) > float(expected_value)
            elif operator == OperatorType.LESS_THAN.value:
                return float(actual_value) < float(expected_value)
            elif operator == OperatorType.EXISTS.value:
                return actual_value is not None and actual_value != ""
            elif operator == OperatorType.REGEX.value:
                import re
                return bool(re.search(str(expected_value), str(actual_value)))
            else:
                return False
        except (ValueError, TypeError):
            self.logger.error(f"Error evaluating condition: {operator} {actual_value} {expected_value}")
            return False

# Global node handler instance
node_handler = WorkflowNodeHandler()

def get_node_config(node_type: str) -> Optional[NodeConfig]:
    """Get configuration for a specific node type"""
    try:
        node_enum = NodeType(node_type)
        return NODE_CONFIGS.get(node_enum)
    except ValueError:
        return None

def validate_node_data(node_type: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate node data against its configuration"""
    config = get_node_config(node_type)
    if not config:
        return {
            "valid": False,
            "errors": [f"Unknown node type: {node_type}"]
        }
    
    # Use Pydantic model for validation
    try:
        data_models = {
            NodeType.GREETING.value: GreetingNodeData,
            NodeType.USER_INPUT.value: UserInputNodeData,
            NodeType.CONDITIONAL.value: ConditionalNodeData,
            NodeType.VOICEMAIL.value: VoicemailNodeData,
            NodeType.TRANSFER.value: TransferNodeData,
            NodeType.REPEAT.value: RepeatNodeData,
            NodeType.END.value: EndNodeData,
            NodeType.AI_ASSISTANT.value: AIAssistantNodeData
        }
        
        model_class = data_models.get(node_type)
        if model_class:
            validated_data = model_class(**node_data)
            return {
                "valid": True,
                "data": validated_data.dict()
            }
        else:
            return {
                "valid": True,
                "data": node_data
            }
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)]
        }

async def execute_workflow_node(node_type: str, node_data: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a workflow node"""
    try:
        node_enum = NodeType(node_type)
        return await node_handler.handle_node(node_enum, node_data, context)
    except ValueError:
        return {
            "success": False,
            "error": f"Unknown node type: {node_type}",
            "action": "error"
        }
    except Exception as e:
        logger.error(f"Error executing node {node_type}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "action": "error"
        }
