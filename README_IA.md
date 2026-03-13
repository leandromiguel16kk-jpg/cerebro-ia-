# Minha IA 100% Privada

Para ter uma inteligência artificial que seja **completamente sua**, onde ninguém pode ver seus dados ou "tomar" ela, você deve rodá-la localmente no seu próprio hardware (PC).

## 1. Como funciona?
Diferente do ChatGPT ou Gemini, que rodam nos servidores da OpenAI ou Google, esta IA rodará no seu computador usando modelos **Open Source** (Código Aberto). Seus dados nunca saem da sua máquina.

## 2. Ferramentas Recomendadas
- **Ollama**: A forma mais fácil de rodar IAs localmente.
- **Llama 3 (Meta)**, **Mistral** ou **Gemma (Google)**: Modelos que você pode baixar e rodar.

## 3. Passo a Passo para Instalação (Windows)
1. Baixe e instale o **Ollama** de [ollama.com](https://ollama.com).
2. Abra o terminal (PowerShell) e digite:
   ```powershell
   ollama run llama3
   ```
3. Pronto! Você já pode conversar com ela 100% offline.

## 5. Rodando em Produção (Railway)
Se você for rodar no Railway ou em outro servidor na nuvem, use o **Groq API** para ter alta performance sem precisar de uma GPU local.

1. Crie uma conta em [console.groq.com](https://console.groq.com).
2. Gere uma API Key.
3. No Railway, adicione as variáveis de ambiente:
   - `GROQ_API_KEY`: Sua chave do Groq.
   - `CHAVE_SECRETA`: Uma senha longa e aleatória para as sessões.
4. O app detectará automaticamente a chave e usará os modelos do Groq.

