import os
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from supabase import create_client
import google.generativeai as genai

app = Flask(__name__)

# Credenciais atualizadas com a sua nova chave do AI Studio
SUPABASE_URL = "https://gnmendbdydjbdrsqqkna.supabase.co"
SUPABASE_KEY = "sb_publishable_gPogwuved8rqGlcq9WJQGw_mcaaEVuB"
GEMINI_API_KEY = "AIzaSyCMfQ3OWN-utRZtOQIYssBJmcyk7hKbaLI"

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
            # Prompt estruturado para JSON limpo
            prompt = (
                f"Extraia os dados desta transação financeira: '{comando}'. "
                "Retorne APENAS um objeto JSON válido, sem formatação Markdown, sem aspas triplas (```json). "
                "Use exatamente estas chaves: "
                '{"tipo": "entrada" ou "saida", "valor": numero, "categoria": "texto", "descricao": "texto"}'
            )
            
            response = model.generate_content(prompt)
            texto_ia = response.text.strip()
            
            # Limpeza caso a IA teime em colocar Markdown
            if texto_ia.startswith("```"):
                texto_ia = texto_ia.replace("```json", "").replace("```", "").strip()
            
            dados = json.loads(texto_ia)
            dados['valor'] = float(dados['valor'])
            
            # SALVANDO NA TABELA: Mantido o nome original com acento conforme seu Supabase
            res = supabase.table("finanças_nuvem").insert(dados).execute()
            
            resp.message(f"✅ Salvo com sucesso no banco!\n💰 Valor: R$ {dados['valor']}\n📂 Categoria: {dados['categoria']}")
        
        except Exception as e:
            print(f"Erro detalhado no servidor: {e}")
            resp.message(f"❌ Erro ao salvar: {str(e)[:50]}")
    
    return str(resp)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)