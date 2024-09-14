import asyncio
import signal

from pydantic_settings import BaseSettings, SettingsConfigDict

from vocode.helpers import create_streaming_microphone_input_and_speaker_output
from vocode.logging import configure_pretty_logging
from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgent
from vocode.streaming.agent.rasa_agent import RasaAgentConfig, RasaAgent
from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.synthesizer import GTTSSynthesizerConfig
from vocode.streaming.models.synthesizer import CartesiaSynthesizerConfig
from vocode.streaming.models.transcriber import (
    DeepgramTranscriberConfig,
    PunctuationEndpointingConfig,
)
from vocode.streaming.streaming_conversation import StreamingConversation
from vocode.streaming.synthesizer.gtts_synthesizer import GTTSSynthesizer
from vocode.streaming.synthesizer.cartesia_synthesizer import CartesiaSynthesizer
from vocode.streaming.transcriber.deepgram_transcriber import DeepgramTranscriber

configure_pretty_logging()


class Settings(BaseSettings):
    """
    Settings for the streaming conversation quickstart.
    These parameters can be configured with environment variables.
    """

    openai_api_key: str = "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"
    # azure_speech_key: str = "ENTER_YOUR_AZURE_KEY_HERE"
    play_ht_speech_key: str = "2c2b193201cb4409a6d55d0620107e54"
    play_ht_user_id: str = "5LUERucEBVMfm1kbF86ruBj8QME2"
    play_ht_voice_id: str = "s3://mockingbird-prod/william_vo_narrative_0eacdff5-6243-4e26-8b3b-66e03458c1d1/voices/speaker/manifest.json"
    eleven_labs_api_key: str = "sk_9e34ee3f49bd907453be86ecb25b0209d9450bf88c8160aa"
    rime_api_key: str = "C7LxIJ-m0G99V_ZyVccjU0G-GubPc4jjwi85Z_OIoKU"
    # "C7LxIJ-m0G99V_ZyVccjU0G-GubPc4jjwi85Z_OIoKU"

    deepgram_api_key: str = "f57e0d42a4d3ebde5aeee25ee35b78fe78e73f1a"
    azure_speech_region: str = "eastus"

    # This means a .env file can be used to overload these settings
    # ex: "OPENAI_API_KEY=my_key" will set openai_api_key over the default above
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


async def main():
    (
        microphone_input,
        speaker_output,
    ) = create_streaming_microphone_input_and_speaker_output(
        use_default_devices=False,
    )

    conversation = StreamingConversation(
        output_device=speaker_output,
        transcriber=DeepgramTranscriber(
            DeepgramTranscriberConfig.from_input_device(
                microphone_input,
                endpointing_config=PunctuationEndpointingConfig(),
                api_key=settings.deepgram_api_key,
            ),
        ),
        agent=RasaAgent(
            RasaAgentConfig(
                webhook="http://0.0.0.0:5005/webhooks/rest/webhook"
            )
        ),
        synthesizer=GTTSSynthesizer(
            GTTSSynthesizerConfig.from_output_device(
                speaker_output
                # voice_id = settings.play_ht_voice_id,
                # api_key = settings.play_ht_speech_key,
                # user_id = settings.play_ht_user_id
                )
            
        ),
    )
    await conversation.start()
    print("Conversation started, press Ctrl+C to end")
    signal.signal(signal.SIGINT, lambda _0, _1: asyncio.create_task(conversation.terminate()))
    while conversation.is_active():
        chunk = await microphone_input.get_audio()
        conversation.receive_audio(chunk)


if __name__ == "__main__":
    asyncio.run(main())
