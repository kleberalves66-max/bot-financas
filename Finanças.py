import os
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from supabase import create_client
import google.generativeai as genai

app = Flask(__name__)

# Variáveis de Ambiente do Render
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://gnmendbdydjbdrsqqkna.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    print("AVISO: Chaves não encontradas no Render!")
    supabase = None
    model = None

@app.route("/webhook", methods=['POST'])
def webhook():
    msg = request.form.get('Body', '').lower()
    resp = MessagingResponse()
    
    if msg.startswith('!bot'):
        comando = msg.replace('!bot', '').strip()
        
        if not model or not supabase:
            resp.message("❌ Erro: Chaves de API não configuradas.")
            return str(resp)
            
        try:
            # 1. IA interpreta o comando natural
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
            
            # 2. Salva o dado atual na tabela financas_nuvem
            supabase.table("financas_nuvem").insert(dados).execute()
            
            # 3. Lógica Avançada: Calcular Saldo Geral para o Alerta
            todas_transacoes = supabase.table("financas_nuvem").select("tipo, valor").execute()
            
            saldo = 0.0
            for t in todas_transacoes.data:
                if t['tipo'] == 'entrada':
                    saldo += float(t['valor'])
                elif t['tipo'] == 'saida':
                    saldo -= float(t['valor'])
            
            # Mensagem base de sucesso
            mensagem_resposta = f"✅ Salvo com sucesso!\n💰 Valor: R$ {dados['valor']}\n📂 Categoria: {dados['categoria']}\n\n📊 Saldo Atual: R$ {saldo:.2f}"
            
            # 4. Alerta de Saldo Baixo (Limite de R$ 200,00)
            LIMITE_ALERTA = 200.00
            if saldo <= LIMITE_ALERTA and dados['tipo'] == 'saida':
                mensagem_resposta += f"\n\n⚠️ *ATENÇÃO, KLEBER!* O teu dinheiro está a acabar. Saldo abaixo de R$ {LIMITE_ALERTA:.2f}!"
                
            resp.message(mensagem_resposta)
        
        except Exception as e:
            print(f"Erro no servidor: {e}")
            resp.message(f"❌ Erro ao processar: {str(e)[:50]}")
    
    return str(resp)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta)
