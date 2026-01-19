import os
import psycopg2
import logging
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

SECRET_KEY = os.getenv("TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎧 *Bem-vind@ ao Assistente de Headsets!*\n\n"
        "Aqui você faz uma busca otimizada.\n"
        "Comandos disponíveis:\n"
        "/baratos [qtd] - Mostra os menores preços (Padrão: 5, Máx: 30)\n"
        "/caros [qtd] - Mostra os maiores preços (Padrão: 5, Máx: 30)\n"
        "/marca [nome] - Busca headsets de uma marca específica\n"
        "/busca [termo] - Busca por uma característica: bluetooth, gamer, cor\n"
        "/aleatorio [qtd] - Sugestões do bot (Máx: 10)"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

def parse_limit(args, default=5, maximum=30):
    if not args:
        return default
    try:
        limit = int(args[0])
        return max(1, min(limit, maximum))
    except ValueError:
        return default

async def cheapest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = parse_limit(context.args, default=5, maximum=30)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "SELECT description, price, link FROM headsets_store ORDER BY price ASC LIMIT %s"
        cur.execute(query, (limit,))
        rows = cur.fetchall()
        
        response = f"*Os {len(rows)} headsets mais baratos:*\n\n"
        for row in rows:
            response += f"R$ {row[1]} - {row[0][:50]}...\n🔗 [Ver Produto]({row[2]})\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
        cur.close()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"Search error: {e}")

async def expensive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = parse_limit(context.args, default=5, maximum=30)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT description, price, link FROM headsets_store ORDER BY price DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        
        response = f"*Os {len(rows)} headsets mais caros:*\n\n"
        for row in rows:
            response += f"R$ {row[1]} - {row[0][:50]}...\n🔗 [Ver Produto]({row[2]})\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
        cur.close()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"Search error: {e}")

async def search_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Por favor, digite a marca. Ex: /marca JBL")
        return
    
    brand = context.args[0]
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "SELECT description, price, link FROM headsets_store WHERE description ILIKE %s LIMIT 10"
        cur.execute(query, (f'%{brand}%',))
        rows = cur.fetchall()
        
        if not rows:
            await update.message.reply_text(f"Nenhum headset da marca '{brand}' encontrado.")
        else:
            response = f"*Modelos da marca {brand.upper()}:*\n\n"
            for row in rows:
                response += f"{row[0][:60]}...\nR$ {row[1]}\n🔗 [Link]({row[2]})\n\n"
            await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
        
        cur.close()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"Search error: {e}")

async def random_headsets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = parse_limit(context.args, default=1, maximum=10)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "SELECT description, price, link FROM headsets_store ORDER BY RANDOM() LIMIT %s"
        cur.execute(query, (limit,))
        rows = cur.fetchall()
        
        response = f"*Sugestão do Bot ({len(rows)}):*\n\n"
        for row in rows:
            response += f"{row[0][:60]}...\nR$ {row[1]}\n🔗 [Link]({row[2]})\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
        cur.close()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"Search error: {e}")

async def search_by_term(update: Update, context: ContextTypes.DEFAULT_TYPE):
    term = " ".join(context.args)
    if not term:
        await update.message.reply_text("Digite um termo para busca. Ex: /busca gamer")
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = "SELECT description, price, link FROM headsets_store WHERE description ILIKE %s LIMIT 5"
        cur.execute(query, (f'%{term}%',))
        rows = cur.fetchall()
        
        if not rows:
            await update.message.reply_text(f"Nada encontrado para '{term}'.")
        else:
            response = f"*Resultados para '{term}':*\n\n"
            for row in rows:
                response += f"{row[0][:60]}...\nR$ {row[1]}\n🔗 [Link]({row[2]})\n\n"
            await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
            
        cur.close()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"Search error: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(SECRET_KEY).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("baratos", cheapest))
    app.add_handler(CommandHandler("caros", expensive))
    app.add_handler(CommandHandler("marca", search_brand))
    app.add_handler(CommandHandler("busca", search_by_term))
    app.add_handler(CommandHandler("aleatorio", random_headsets))
    
    print("Bot em execução...")
    app.run_polling()