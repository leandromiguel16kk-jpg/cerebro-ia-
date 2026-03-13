import ollama

def chat():
    print("--- Minha IA Privada 1.0 (Local) ---")
    print("Digite 'sair' para encerrar.\n")
    
    # Histórico de mensagens
    messages = []
    
    while True:
        user_input = input("Você: ")
        
        if user_input.lower() == 'sair':
            break
            
        # Adiciona a mensagem do usuário ao histórico
        messages.append({'role': 'user', 'content': user_input})
        
        try:
            # Chama a IA local (exemplo usando llama3.2:latest)
            # Para rodar isso, você deve ter instalado o Ollama e rodado 'ollama pull llama3.2:latest' no terminal.
            response = ollama.chat(model='llama3.2:latest', messages=messages)
            
            ia_response = response['message']['content']
            print(f"\nIA: {ia_response}\n")
            
            # Adiciona a resposta da IA ao histórico
            messages.append({'role': 'assistant', 'content': ia_response})
            
        except Exception as e:
            print(f"\nErro ao falar com a IA: {e}")
            print("Verifique se o Ollama está rodando e se você baixou o modelo (ollama run llama3).\n")

if __name__ == "__main__":
    chat()
