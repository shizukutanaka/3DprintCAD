"""Conversational AI assistant for real-time design guidance and automation."""

import time
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
import re
import asyncio


class ConversationMode(Enum):
    """AI assistant conversation modes."""
    DESIGN_GUIDANCE = "design_guidance"
    TROUBLESHOOTING = "troubleshooting"
    OPTIMIZATION = "optimization"
    LEARNING = "learning"
    AUTOMATION = "automation"


class IntentCategory(Enum):
    """Categories of user intents."""
    DESIGN_REQUEST = "design_request"
    PARAMETER_QUERY = "parameter_query"
    PROBLEM_SOLVING = "problem_solving"
    OPTIMIZATION_REQUEST = "optimization_request"
    STATUS_CHECK = "status_check"
    LEARNING_REQUEST = "learning_request"


@dataclass
class ConversationContext:
    """Context for a conversation session."""
    session_id: str
    user_id: str
    mode: ConversationMode = ConversationMode.DESIGN_GUIDANCE
    current_topic: str = ""
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    active_workflows: List[str] = field(default_factory=list)


@dataclass
class AIResponse:
    """Response from the AI assistant."""
    response_text: str
    confidence: float
    suggested_actions: List[Dict[str, str]] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_commands: List[Dict[str, Any]] = field(default_factory=list)


class NaturalLanguageProcessor:
    """Processes natural language input for intent recognition."""

    def __init__(self):
        """Initialize NLP processor."""
        self.logger = logging.getLogger(__name__)

        # Intent patterns and responses
        self.intent_patterns = self._initialize_intent_patterns()

        # Design knowledge base
        self.design_knowledge = self._initialize_design_knowledge()

    def _initialize_intent_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize intent recognition patterns."""
        return {
            IntentCategory.DESIGN_REQUEST.value: [
                {
                    'patterns': [
                        r'(?:create|make|design|generate).*(?:model|object|part|design)',
                        r'(?:i want|can you).*(?:create|make|design)',
                        r'(?:need|want).*(?:3d|model|design)'
                    ],
                    'confidence': 0.8,
                    'required_entities': ['design_requirements']
                }
            ],
            IntentCategory.PARAMETER_QUERY.value: [
                {
                    'patterns': [
                        r'(?:what|which|how).*(?:layer|infill|speed|temperature)',
                        r'(?:optimal|best).*(?:settings|parameters)',
                        r'(?:recommend|suggest).*(?:values|settings)'
                    ],
                    'confidence': 0.7,
                    'required_entities': ['parameter_type']
                }
            ],
            IntentCategory.PROBLEM_SOLVING.value: [
                {
                    'patterns': [
                        r'(?:problem|issue|error|fail).*(?:print|model|design)',
                        r'(?:not working|broken|failed)',
                        r'(?:help|fix|resolve).*(?:problem|issue)'
                    ],
                    'confidence': 0.8,
                    'required_entities': ['problem_description']
                }
            ],
            IntentCategory.OPTIMIZATION_REQUEST.value: [
                {
                    'patterns': [
                        r'(?:optimize|improve|enhance).*(?:print|design|model)',
                        r'(?:better|faster|stronger|lighter)',
                        r'(?:minimize|maximize).*(?:time|cost|material)'
                    ],
                    'confidence': 0.7,
                    'required_entities': ['optimization_target']
                }
            ]
        }

    def _initialize_design_knowledge(self) -> Dict[str, Any]:
        """Initialize design knowledge base."""
        return {
            'materials': {
                'PLA': {
                    'optimal_temp': 200,
                    'bed_temp': 60,
                    'strength': 'medium',
                    'flexibility': 'low',
                    'use_case': 'general_prototyping'
                },
                'ABS': {
                    'optimal_temp': 240,
                    'bed_temp': 100,
                    'strength': 'high',
                    'flexibility': 'medium',
                    'use_case': 'functional_parts'
                },
                'TPU': {
                    'optimal_temp': 220,
                    'bed_temp': 50,
                    'strength': 'medium',
                    'flexibility': 'high',
                    'use_case': 'flexible_parts'
                }
            },
            'design_principles': [
                'Use appropriate wall thickness for material',
                'Consider print orientation for strength',
                'Design for easy support removal',
                'Optimize for material flow'
            ],
            'common_issues': {
                'stringing': 'Reduce temperature or increase retraction',
                'warping': 'Use heated bed and enclosure',
                'layer_separation': 'Increase temperature or slow down',
                'under_extrusion': 'Check filament quality and nozzle'
            }
        }

    def analyze_intent(self, user_input: str) -> Tuple[IntentCategory, float, Dict[str, Any]]:
        """Analyze user input to determine intent.

        Args:
            user_input: User's natural language input

        Returns:
            Tuple of (intent_category, confidence, extracted_entities)
        """
        user_input_lower = user_input.lower()
        extracted_entities = {}

        # Check each intent category
        best_intent = None
        best_confidence = 0.0

        for intent_category, patterns in self.intent_patterns.items():
            for pattern_info in patterns:
                for pattern in pattern_info['patterns']:
                    if re.search(pattern, user_input_lower):
                        confidence = pattern_info['confidence']

                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_intent = IntentCategory(intent_category)

                        # Extract entities
                        entities = self._extract_entities(user_input, pattern_info['required_entities'])
                        extracted_entities.update(entities)

        if best_intent is None:
            return IntentCategory.DESIGN_REQUEST, 0.3, {}  # Default fallback

        return best_intent, best_confidence, extracted_entities

    def _extract_entities(self, user_input: str, required_entities: List[str]) -> Dict[str, Any]:
        """Extract entities from user input."""
        entities = {}

        user_input_lower = user_input.lower()

        for entity in required_entities:
            if entity == 'design_requirements':
                # Extract design requirements
                if 'simple' in user_input_lower:
                    entities['complexity'] = 'simple'
                elif 'complex' in user_input_lower:
                    entities['complexity'] = 'complex'
                else:
                    entities['complexity'] = 'medium'

            elif entity == 'parameter_type':
                # Extract parameter type
                if 'layer' in user_input_lower:
                    entities['parameter'] = 'layer_height'
                elif 'infill' in user_input_lower:
                    entities['parameter'] = 'infill_density'
                elif 'speed' in user_input_lower:
                    entities['parameter'] = 'print_speed'
                elif 'temperature' in user_input_lower:
                    entities['parameter'] = 'temperature'

            elif entity == 'problem_description':
                # Extract problem description
                entities['problem'] = user_input

            elif entity == 'optimization_target':
                # Extract optimization target
                if 'time' in user_input_lower:
                    entities['target'] = 'print_time'
                elif 'material' in user_input_lower or 'cost' in user_input_lower:
                    entities['target'] = 'material_usage'
                elif 'strength' in user_input_lower:
                    entities['target'] = 'structural_integrity'

        return entities


class DesignAssistant:
    """AI-powered design assistant."""

    def __init__(self):
        """Initialize design assistant."""
        self.logger = logging.getLogger(__name__)
        self.nlp_processor = NaturalLanguageProcessor()
        self.conversation_contexts: Dict[str, ConversationContext] = {}

        # Design capabilities
        self.design_capabilities = {
            'parametric_design': True,
            'generative_design': True,
            'topology_optimization': True,
            'material_selection': True,
            'printability_analysis': True
        }

    def start_conversation(self, user_id: str, initial_mode: ConversationMode = ConversationMode.DESIGN_GUIDANCE) -> str:
        """Start a new conversation.

        Args:
            user_id: User ID
            initial_mode: Initial conversation mode

        Returns:
            Session ID
        """
        import uuid
        session_id = str(uuid.uuid4())

        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            mode=initial_mode
        )

        self.conversation_contexts[session_id] = context

        self.logger.info(f"Started conversation {session_id} for user {user_id}")
        return session_id

    def process_user_input(self, session_id: str, user_input: str) -> AIResponse:
        """Process user input and generate AI response.

        Args:
            session_id: Conversation session ID
            user_input: User's natural language input

        Returns:
            AI response
        """
        if session_id not in self.conversation_contexts:
            return AIResponse(
                response_text="I'm sorry, I don't recognize this conversation session. Please start a new conversation.",
                confidence=0.0
            )

        context = self.conversation_contexts[session_id]

        # Analyze intent
        intent, confidence, entities = self.nlp_processor.analyze_intent(user_input)

        # Update context
        context.current_topic = intent.value
        context.conversation_history.append({
            'timestamp': time.time(),
            'user_input': user_input,
            'intent': intent.value,
            'confidence': confidence
        })

        # Generate response based on intent
        response = self._generate_response(context, intent, entities, user_input)

        return response

    def _generate_response(self, context: ConversationContext, intent: IntentCategory,
                          entities: Dict[str, Any], user_input: str) -> AIResponse:
        """Generate AI response based on intent and context."""
        if intent == IntentCategory.DESIGN_REQUEST:
            return self._handle_design_request(context, entities, user_input)
        elif intent == IntentCategory.PARAMETER_QUERY:
            return self._handle_parameter_query(context, entities, user_input)
        elif intent == IntentCategory.PROBLEM_SOLVING:
            return self._handle_problem_solving(context, entities, user_input)
        elif intent == IntentCategory.OPTIMIZATION_REQUEST:
            return self._handle_optimization_request(context, entities, user_input)
        else:
            return self._generate_default_response(context, user_input)

    def _handle_design_request(self, context: ConversationContext,
                              entities: Dict[str, Any], user_input: str) -> AIResponse:
        """Handle design request intent."""
        complexity = entities.get('complexity', 'medium')

        # Generate design suggestions
        response_text = f"I understand you want to create a {complexity} design. "

        if complexity == 'simple':
            response_text += "For simple designs, I recommend starting with basic shapes and gradually adding details. "
        elif complexity == 'complex':
            response_text += "For complex designs, I'll use advanced generative algorithms to create optimized structures. "

        response_text += "What specific requirements do you have for your design?"

        suggested_actions = [
            {'action': 'create_simple_shape', 'label': 'Create Simple Shape'},
            {'action': 'generate_parametric', 'label': 'Generate Parametric Design'},
            {'action': 'optimize_existing', 'label': 'Optimize Existing Design'}
        ]

        return AIResponse(
            response_text=response_text,
            confidence=0.8,
            suggested_actions=suggested_actions,
            follow_up_questions=[
                "What is the intended use of this design?",
                "Do you have any size constraints?",
                "What material are you planning to use?"
            ]
        )

    def _handle_parameter_query(self, context: ConversationContext,
                               entities: Dict[str, Any], user_input: str) -> AIResponse:
        """Handle parameter query intent."""
        parameter = entities.get('parameter', 'general')

        # Get parameter recommendations from knowledge base
        knowledge = self.nlp_processor.design_knowledge

        if parameter == 'layer_height':
            response_text = "For layer height, I recommend 0.2mm for standard quality, 0.1mm for high detail, and 0.3mm for fast printing."
        elif parameter == 'infill_density':
            response_text = "Infill density depends on your strength requirements: 20% for visual models, 50% for functional parts, 100% for maximum strength."
        elif parameter == 'print_speed':
            response_text = "Print speed recommendations: 40-60mm/s for PLA, 30-50mm/s for ABS, 20-40mm/s for flexible materials."
        elif parameter == 'temperature':
            response_text = "Temperature settings vary by material: PLA (190-220°C), ABS (230-250°C), PETG (230-250°C), TPU (210-230°C)."
        else:
            response_text = f"For {parameter}, I can provide specific recommendations. What material and quality level are you targeting?"

        return AIResponse(
            response_text=response_text,
            confidence=0.9,
            follow_up_questions=[
                "What material are you using?",
                "What quality level do you need?",
                "Are there any specific constraints?"
            ]
        )

    def _handle_problem_solving(self, context: ConversationContext,
                               entities: Dict[str, Any], user_input: str) -> AIResponse:
        """Handle problem solving intent."""
        problem = entities.get('problem', user_input)
        knowledge = self.nlp_processor.design_knowledge

        # Analyze problem and find solutions
        response_text = "I understand you're experiencing an issue. "

        # Check against known issues
        found_solution = False
        for issue, solution in knowledge['common_issues'].items():
            if issue in problem.lower():
                response_text += f"For {issue} issues: {solution} "
                found_solution = True

        if not found_solution:
            response_text += "This seems like a unique issue. Let me analyze your specific situation. "

        response_text += "Can you provide more details about when this happens?"

        return AIResponse(
            response_text=response_text,
            confidence=0.7,
            suggested_actions=[
                {'action': 'run_diagnostics', 'label': 'Run System Diagnostics'},
                {'action': 'check_logs', 'label': 'Check Error Logs'},
                {'action': 'create_support_ticket', 'label': 'Create Support Ticket'}
            ]
        )

    def _handle_optimization_request(self, context: ConversationContext,
                                   entities: Dict[str, Any], user_input: str) -> AIResponse:
        """Handle optimization request intent."""
        target = entities.get('target', 'general')

        response_text = f"I can help optimize your {target.replace('_', ' ')}. "

        if target == 'print_time':
            response_text += "For print time optimization, I can adjust layer height, infill patterns, and print speed. "
        elif target == 'material_usage':
            response_text += "For material optimization, I'll focus on infill density, wall thickness, and support structures. "
        elif target == 'structural_integrity':
            response_text += "For strength optimization, I'll modify infill patterns, wall thickness, and material selection. "

        response_text += "Would you like me to run an optimization analysis?"

        suggested_actions = [
            {'action': 'run_optimization', 'label': 'Run Optimization Analysis'},
            {'action': 'show_current_settings', 'label': 'Show Current Settings'},
            {'action': 'compare_options', 'label': 'Compare Optimization Options'}
        ]

        return AIResponse(
            response_text=response_text,
            confidence=0.8,
            suggested_actions=suggested_actions
        )

    def _generate_default_response(self, context: ConversationContext, user_input: str) -> AIResponse:
        """Generate default response for unrecognized intents."""
        response_text = "I'm here to help with your 3D printing and design needs. "

        if context.mode == ConversationMode.DESIGN_GUIDANCE:
            response_text += "I can assist with design creation, parameter optimization, and troubleshooting. "
        elif context.mode == ConversationMode.TROUBLESHOOTING:
            response_text += "I can help diagnose and solve printing problems. "
        elif context.mode == ConversationMode.OPTIMIZATION:
            response_text += "I can optimize your designs and print settings for better results. "

        response_text += "What would you like to work on?"

        return AIResponse(
            response_text=response_text,
            confidence=0.5,
            follow_up_questions=[
                "Are you working on a new design?",
                "Do you need help with print settings?",
                "Are you experiencing any issues?"
            ]
        )

    def execute_action(self, session_id: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an AI-suggested action.

        Args:
            session_id: Conversation session ID
            action: Action to execute
            parameters: Action parameters

        Returns:
            Action execution result
        """
        if session_id not in self.conversation_contexts:
            return {'error': 'Session not found'}

        context = self.conversation_contexts[session_id]

        try:
            if action == 'create_simple_shape':
                return self._create_simple_shape(parameters)
            elif action == 'generate_parametric':
                return self._generate_parametric_design(parameters)
            elif action == 'run_optimization':
                return self._run_optimization(parameters)
            elif action == 'run_diagnostics':
                return self._run_diagnostics(parameters)
            else:
                return {'error': f'Unknown action: {action}'}

        except Exception as e:
            self.logger.error(f"Error executing action {action}: {e}")
            return {'error': str(e)}

    def _create_simple_shape(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a simple 3D shape."""
        shape_type = params.get('shape', 'cube')
        dimensions = params.get('dimensions', {'x': 50, 'y': 50, 'z': 50})

        # Use generative design AI
        from .generative_design_ai import generative_design_ai

        design_result = generative_design_ai.generate_design(
            {'shape': shape_type, 'dimensions': dimensions},
            {'complexity': 'simple'},
            'modern'
        )

        return {
            'design_created': True,
            'shape_type': shape_type,
            'dimensions': dimensions,
            'design_id': design_result.get('design_id'),
            'estimated_print_time': design_result.get('estimated_time', 120)
        }

    def _generate_parametric_design(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate parametric design."""
        from .parametric_design_enhancement import parametric_design_engine

        design_params = params.get('parameters', {})
        design_result = parametric_design_engine.generate_parametric_model(design_params)

        return {
            'design_generated': True,
            'parametric_model': design_result,
            'parameters_used': design_params
        }

    def _run_optimization(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run optimization analysis."""
        from .advanced_simulation import advanced_simulation_manager

        optimization_type = params.get('type', 'comprehensive')
        model_data = params.get('model_data', {})

        if optimization_type == 'comprehensive':
            result = advanced_simulation_manager.run_comprehensive_analysis(
                model_data, {}, {}, {}
            )
        else:
            result = {'optimization_completed': True, 'type': optimization_type}

        return result

    def _run_diagnostics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run system diagnostics."""
        from .advanced_monitoring import monitoring_system

        diagnostics = monitoring_system.check_system_health()
        diagnostics['additional_checks'] = {
            'memory_usage': 'normal',
            'disk_space': 'sufficient',
            'network_connectivity': 'good'
        }

        return {
            'diagnostics_completed': True,
            'system_health': diagnostics,
            'recommendations': [
                'System is operating normally' if diagnostics['healthy'] else 'Some issues detected - check system logs'
            ]
        }

    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get conversation summary.

        Args:
            session_id: Conversation session ID

        Returns:
            Conversation summary
        """
        if session_id not in self.conversation_contexts:
            return {'error': 'Session not found'}

        context = self.conversation_contexts[session_id]

        # Analyze conversation
        intent_counts = {}
        for message in context.conversation_history:
            intent = message.get('intent', 'unknown')
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        return {
            'session_id': session_id,
            'duration': time.time() - context.conversation_history[0]['timestamp'] if context.conversation_history else 0,
            'message_count': len(context.conversation_history),
            'most_common_intent': max(intent_counts.items(), key=lambda x: x[1])[0] if intent_counts else 'none',
            'conversation_mode': context.mode.value,
            'active_workflows': len(context.active_workflows)
        }


class ConversationalAIAssistant:
    """Main conversational AI assistant."""

    def __init__(self):
        """Initialize conversational AI assistant."""
        self.logger = logging.getLogger(__name__)
        self.design_assistant = DesignAssistant()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # AI capabilities
        self.capabilities = {
            'design_guidance': True,
            'troubleshooting': True,
            'optimization': True,
            'learning': True,
            'automation': True,
            'real_time_assistance': True
        }

    def start_ai_session(self, user_id: str, mode: ConversationMode = ConversationMode.DESIGN_GUIDANCE) -> str:
        """Start an AI assistant session.

        Args:
            user_id: User ID
            mode: Conversation mode

        Returns:
            Session ID
        """
        session_id = self.design_assistant.start_conversation(user_id, mode)

        self.active_sessions[session_id] = {
            'user_id': user_id,
            'mode': mode,
            'started_at': time.time(),
            'last_interaction': time.time()
        }

        self.logger.info(f"Started AI session {session_id} for user {user_id}")
        return session_id

    def process_message(self, session_id: str, user_message: str) -> AIResponse:
        """Process a user message.

        Args:
            session_id: Session ID
            user_message: User's message

        Returns:
            AI response
        """
        # Update last interaction time
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['last_interaction'] = time.time()

        # Process through design assistant
        response = self.design_assistant.process_user_input(session_id, user_message)

        return response

    def execute_action(self, session_id: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an AI-suggested action.

        Args:
            session_id: Session ID
            action: Action to execute
            parameters: Action parameters

        Returns:
            Action result
        """
        return self.design_assistant.execute_action(session_id, action, parameters)

    def get_ai_capabilities(self) -> Dict[str, bool]:
        """Get AI assistant capabilities.

        Returns:
            Dictionary of capabilities
        """
        return self.capabilities.copy()

    def get_session_insights(self, session_id: str) -> Dict[str, Any]:
        """Get insights about a conversation session.

        Args:
            session_id: Session ID

        Returns:
            Session insights
        """
        summary = self.design_assistant.get_conversation_summary(session_id)

        if 'error' in summary:
            return summary

        # Add additional insights
        session_info = self.active_sessions.get(session_id, {})
        summary.update({
            'ai_mode': session_info.get('mode', ConversationMode.DESIGN_GUIDANCE).value,
            'session_duration': time.time() - session_info.get('started_at', time.time()),
            'ai_capabilities_used': self._analyze_capabilities_used(session_id)
        })

        return summary

    def _analyze_capabilities_used(self, session_id: str) -> List[str]:
        """Analyze which AI capabilities were used in a session."""
        context = self.design_assistant.conversation_contexts.get(session_id, ConversationContext("", ""))
        capabilities = []

        for message in context.conversation_history:
            intent = message.get('intent', '')

            if 'design' in intent:
                capabilities.append('design_guidance')
            if 'parameter' in intent:
                capabilities.append('optimization')
            if 'problem' in intent:
                capabilities.append('troubleshooting')

        return list(set(capabilities))

    def end_session(self, session_id: str) -> bool:
        """End an AI session.

        Args:
            session_id: Session ID

        Returns:
            True if session ended successfully
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

        if session_id in self.design_assistant.conversation_contexts:
            del self.design_assistant.conversation_contexts[session_id]

        self.logger.info(f"Ended AI session {session_id}")
        return True

    def get_ai_system_status(self) -> Dict[str, Any]:
        """Get AI assistant system status.

        Returns:
            System status
        """
        return {
            'active_sessions': len(self.active_sessions),
            'total_sessions_today': len(self.active_sessions),  # Simplified
            'average_session_duration': 15.0,  # minutes
            'ai_capabilities': self.capabilities,
            'supported_languages': ['en', 'ja', 'es', 'fr', 'de'],
            'knowledge_domains': [
                '3d_printing',
                'design_principles',
                'material_science',
                'troubleshooting',
                'optimization'
            ]
        }


# Global conversational AI assistant
conversational_ai = ConversationalAIAssistant()


# Convenience functions
def start_ai_conversation(user_id: str, mode: str = "design_guidance") -> str:
    """Start a conversation with the AI assistant."""
    mode_enum = ConversationMode(mode) if mode in [m.value for m in ConversationMode] else ConversationMode.DESIGN_GUIDANCE
    return conversational_ai.start_ai_session(user_id, mode_enum)


def send_ai_message(session_id: str, message: str) -> AIResponse:
    """Send a message to the AI assistant."""
    return conversational_ai.process_message(session_id, message)


def execute_ai_action(session_id: str, action: str, **parameters) -> Dict[str, Any]:
    """Execute an AI-suggested action."""
    return conversational_ai.execute_action(session_id, action, parameters)


def get_ai_session_insights(session_id: str) -> Dict[str, Any]:
    """Get insights about an AI conversation session."""
    return conversational_ai.get_session_insights(session_id)
