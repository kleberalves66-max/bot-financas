import os
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from supabase import create_client, Client

# --- CONFIGURAÇÃO FLASK ---
app = Flask(__name__)

# --- CONFIGURAÇÃO SUPABASE ---
SUPABASE_URL = "https://gnmendbdydjdbrsqqkna.supabase.co"
# ATENÇÃO: Cole sua chave real do Supabase entre as aspas abaixo
SUPABASE_KEY = "SUA_CHAVE_SECRETA_DO_SUPABASE_AQUI" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CONFIGURAÇÃO GEMINI ---
GENAI_API_KEY = "AIzaSyCMfQ3OWN-utRZtOQlYssBJmcyk7hKbaLI"
client_gemini = genai.Client(api_key=GENAI_API_KEY)

# --- PROMPT DO SISTEMA ---
PROMPT_SISTEMA = """
Você é um assistente financeiro pessoal altamente inteligente. 
Sua tarefa é ler uma frase sobre finanças enviada pelo usuário e extrair os dados estritamente em formato JSON válido.
Não adicione nenhuma formatação Markdown (nunca use ```json ou ```). Retorne apenas o objeto JSON puro.

Você deve identificar obrigatoriamente estes 4 campos com estes nomes exatos em letras minúsculas:
1. "tipo": deve ser estritamente 'entrada' ou 'saida'.
2. "valor": um número decimal (float) representando o valor.
3. "categoria": a categoria do registro (ex: Salário, Alimentação, Transporte, Contas Fixas, Lazer, Rendimentos).
4. "descricao": um breve resumo em português do que se trata.
"""

@app.route("/webhook", methods=["POST"])
def webhook():
    mensagem_usuario = request.values.get("Body", "").strip()
    resposta_twilio = MessagingResponse()

    if mensagem_usuario.lower().startswith("!bot "):
        comando_financeiro = mensagem_usuario[5:].strip()
        
        try:
            print(f"\n--- Nova mensagem recebida: '{comando_financeiro}' ---")
            
            resposta_ia = client_gemini.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"{PROMPT_SISTEMA}\n\nAnalise a frase: {comando_financeiro}"
            )
            texto_ia = resposta_ia.text.strip()
            
            print(f"Resposta bruta da IA: {texto_ia}")
            dados_da_ia = json.loads(texto_ia)
            
            categoria_ia = dados_da_ia.get("categoria") or dados_da_ia.get("Categoria")
            tipo_ia = dados_da_ia.get("tipo") or dados_da_ia.get("Tipo") or "saida"
            valor_ia = dados_da_ia.get("valor") or dados_da_ia.get("Valor") or 0.0
            descricao_ia = dados_da_ia.get("descricao") or dados_da_ia.get("Descrição") or "Registro financeiro"

            if not categoria_ia:
                categoria_ia = "Salário" if str(tipo_ia).lower() == "entrada" else "Outros"
            
            dados_para_salvar = {
                "tipo": str(tipo_ia).lower(),
                "valor": float(valor_ia),
                "categoria": str(categoria_ia),
                "descricao": str(descricao_ia)
            }
            
            print(f"Dados estruturados para salvar: {dados_para_salvar}")
            
            supabase.table("finanças_nuvem").insert(dados_para_salvar).execute()
            print("✅ Registro salvo com sucesso no Supabase!")
            
            emoji_tipo = "💰" if dados_para_salvar["tipo"] == "entrada" else "💸"
            titulo_registro = "Faturamento Salvo!" if dados_para_salvar["tipo"] == "entrada" else "Registro Salvo no Supabase!"
            
            mensagem_retorno = (
                f"✅ *{titulo_registro}*\n\n"
                f"{emoji_tipo} *Valor:* R$ {dados_para_salvar['valor']:.2f}\n"
                f"🏷️ *Categoria:* {dados_para_salvar['categoria']}\n"
                f"📝 *Descrição:* {dados_para_salvar['descricao']}"
            )
            
        except json.JSONDecodeError:
            print("❌ Erro: O Gemini não retornou um JSON válido.")
            mensagem_retorno = "❌ Desculpe, não consegui estruturar os dados dessa mensagem."
        except Exception as e:
            print(f"❌ Erro detalhado ao salvar no Supabase: {e}")
            mensagem_retorno = "❌ Ocorreu um erro ao tentar salvar os dados no banco de dados."
            
        resposta_twilio.message(mensagem_retorno)
    
    return str(resposta_twilio)

if __name__ == "__main__":
    print("\n🚀 Iniciando o servidor do Bot...")
    app.run(port=5000, debug=True)