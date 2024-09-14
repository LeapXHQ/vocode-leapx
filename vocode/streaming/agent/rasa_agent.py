import requests
from vocode.streaming.models.agent import AgentConfig
from typing import Optional, Tuple, AsyncGenerator
from vocode.streaming.agent.base_agent import GeneratedResponse, RespondAgent, StreamedResponse
from vocode.streaming.models.transcript import ActionStart, EventLog, Transcript
from vocode.streaming.models.message import BaseMessage, LLMToken
from vocode.streaming.agent.openai_utils import merge_event_logs


class RasaAgentConfig(AgentConfig, type="rasa"):
    webhook: str 

class RasaAgent(RespondAgent[RasaAgentConfig]):
    def __init__(
        self,
        agent_config: RasaAgentConfig,
    ):
        super().__init__(agent_config=agent_config)

    @staticmethod
    def _format_rasa_chat_messages_from_transcript(transcript: Transcript,) -> dict:
        # merge consecutive bot messages
        new_event_logs: list[EventLog] = merge_event_logs(event_logs=transcript.event_logs)

        # Removing BOT_ACTION_START so that it doesn't confuse the completion-y prompt, e.g.
        # BOT: BOT_ACTION_START: action_end_conversation
        # Right now, this version of context does not work for normal actions, only phrase trigger actions

        merged_event_logs_sans_bot_action_start = [
            event_log for event_log in new_event_logs if not isinstance(event_log, ActionStart)
        ]

        return {
            "sender": "user",
            "message": Transcript(event_logs=merged_event_logs_sans_bot_action_start).to_string(
                    include_timestamps=False,
                    mark_human_backchannels_with_brackets=True,
                )
        }
        

    # is_interrupt is True when the human has just interrupted the bot's last response
    def respond(
        self, human_input, is_interrupt: bool = False
    ) -> tuple[Optional[str], bool]:
        pass

    async def generate_response(
        self,
        human_input,
        conversation_id: str,
        is_interrupt: bool = False,
        bot_was_in_medias_res: bool = False,
    ) -> AsyncGenerator[Tuple[str, bool], None]: # message and whether or not the message is interruptible
        """Returns a generator that yields the agent's response one sentence at a time."""
        if not self.transcript:
            raise ValueError("A transcript is not attached to the agent")
        messages = self._format_rasa_chat_messages_from_transcript(transcript=self.transcript)
        rasa_response = requests.post(self.agent_config.webhook, json=messages)
        response_json = rasa_response.json()

        using_input_streaming_synthesizer = (
            self.conversation_state_manager.using_input_streaming_synthesizer()
        )
        ResponseClass = (
            StreamedResponse if using_input_streaming_synthesizer else GeneratedResponse
        )
        MessageType = LLMToken if using_input_streaming_synthesizer else BaseMessage

        for message in response_json:
            yield ResponseClass(
                message=MessageType(text=message['text']),
                is_interruptible=True,
            )