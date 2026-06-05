import os
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from supabase import create_client
import google.generativeai as genai

app = Flask(__name__)

# Puxando dos Environments do Render
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://gnmendbdydjbdrsqqkna.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Inicialização com o nome simplificado do modelo para projetos novos
if GEMINI_API_KEY and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("AVISO: Chaves não encontradas nas Variáveis de Ambiente do Render!")
    supabase = None
    model = None

@app.route("/webhook", methods=['POST'])
def webhook():
    msg = request.form.get('Body', '').lower()
    resp = MessagingResponse()
    
    if msg.startswith('!bot'):
        comando = msg.replace('!bot', '').strip()
        
        if not model or not supabase:
            resp.message("❌ Erro: O servidor iniciou, mas as chaves de API não estão configuradas no Render.")
            return str(resp)
            
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
