# Kurulum Komutlar
.venv\Scripts\activate.bat
uv pip install -r bimconverse/requirements.txt
python -m bimconverse.cli --create-config

# Geliştirmeler
OpenAILLM kullanılan yerler Gemini ile çalışabilir hale getirilecek.

## config.json
```json
  "neo4j": {
    "uri": "neo4j://localhost:7687",
    "username": "neo4j",
    "password": "test1234",
    "database": "neo4j"
  },
  "openai": {
    "api_key": "AIzaSyBXl1PlLb8MRlEuquS53X3RjTVmuh9Y_SA",
    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "llm_model": "gemini-2.5-flash",
    "temperature": 0.1
  },
```

# Çalıştırma Komutları
- .venv\Scripts\activate.bat
- cd ifc_knowledge_graph
- python optimized_processor_runner.py data/ifc_files/Duplex_A_20110907.ifc --password test1234 --database ifcdb
- python -m bimconverse.cli --config config.json
  - What spaces are on the ground floor?
  - Zemin katta hangi odalar var?


# LLM Debug

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('openai_llm.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

            if isinstance(message_history, MessageHistory):
                message_history = message_history.messages
            logger.debug(f"-------- Sending message: {input}")
            response = self.client.chat.completions.create(
                messages=self.get_messages(input, message_history, system_instruction),
                model=self.model_name,
                **self.model_params,
            )
            content = response.choices[0].message.content or ""
            logger.debug(f"-------- Received response: {content}")