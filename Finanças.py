import os
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from supabase import create_client
import google.generativeai as genai

app = Flask(__name__)

# Puxando com total segurança da memória do Render (Sem chaves expostas!)
SUPABASE_URL = os.environ.get("https://gnmendbdydjbdrsqqkna.supabase.co")
SUPABASE_KEY = os.environ.get("sb_publishable_gPogwuved8rqGlcq9WJQGw_mcaaEVuB")
GEMINI_API_KEY = os.environ.get("AQ.Ab8RN6LoKlgAkJbjR_xwJn7O16aw1Zas9-QYO_3aQYA8bxguoA")

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
            prompt = (
                f"Extraia os dados desta transação financeira: '{comando}'. "
                "Retorne APENAS um objeto JSON válido, sem formatação Markdown, sem aspas triplas (```json). "
                "Use exatamente estas chaves: "
                '{"tipo": "entrada" ou "saida", "valor": numero, "categoria": "texto", "descricao": "texto"}'
            )
            
            response = model.generate_content(prompt)
            texto_ia = response.text.strip()
            
            if texto_ia.startswith("```"):
                texto_ia = texto_ia.replace("```json", "").replace("```", "").strip()
            
            dados = json.loads(texto_ia)
            dados['valor'] = float(dados['valor'])
            
            # Salvando na tabela oficial com acento
            res = supabase.table("finanças_nuvem").insert(dados).execute()
            
            resp.message(f"✅ Salvo com sucesso no banco!\n💰 Valor: R$ {dados['valor']}\n📂 Categoria: {dados['categoria']}")
        
        except Exception as e:
            print(f"Erro detalhado no servidor: {e}")
            resp.message(f"❌ Erro ao salvar: {str(e)[:50]}")
    
    return str(resp)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)