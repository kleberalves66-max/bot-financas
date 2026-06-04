import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from supabase import create_client
import google.generativeai as genai

app = Flask(__name__)

# Credenciais configuradas conforme seu painel do Render
SUPABASE_URL = "https://gnmendbdydjbdrsqqkna.supabase.co"
SUPABASE_KEY = "sb_publishable_gPogwuved8rqGlcq9WJQGw_mcaaEVuB"
GEMINI_API_KEY = "AQ.Ab8RN6Jr-pHY0g12qKzGW0BtkWMqEtd5-Bgqq019gDQ_6KrkvQ"

# Inicialização dos Clientes
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route("/webhook", methods=['POST'])
def webhook():
    msg = request.form.get('Body', '').lower()
    resp = MessagingResponse()
    
    if msg.startswith('!bot'):
        comando = msg.replace('!bot', '').strip()
        
        try:
            # IA processando a frase
            prompt = f"Extraia os dados desta transação financeira: '{comando}'. Retorne APENAS um JSON com: tipo (entrada/saida), valor (numero), categoria e descricao."
            response = model.generate_content(prompt)
            
            # Limpeza do texto da IA para garantir que seja um JSON válido
            json_text = response.text.replace('```json', '').replace('```', '').strip()
            dados = eval(json_text)
            
            # AJUSTADO: Nome da tabela limpo, sem acentos para rodar na nuvem
            res = supabase.table("financas_nuvem").insert(dados).execute()
            
            resp.message(f"✅ Salvo com sucesso no banco!\n💰 Valor: R$ {dados['valor']}\n📂 Categoria: {dados['categoria']}")
        
        except Exception as e:
            print(f"Erro detalhado: {e}")
            resp.message("❌ Ocorreu um erro ao processar ou salvar no banco de dados.")
    
    return str(resp)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)