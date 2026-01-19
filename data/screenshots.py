import os
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

output_dir = "screenshots"
os.makedirs(output_dir, exist_ok=True)

opt = Options()
opt.add_argument("-private")
opt.set_preference("browser.privatebrowsing.autostart", True)
opt.add_argument("--width=1280")
opt.add_argument("--height=700")

browser = webdriver.Firefox(options=opt)
url_base = 'https://lista.mercadolivre.com.br/headset#D[A:headset]'
browser.get(url_base)
sleep(3)

def remove_popups():
    script = """
    // Remove login do Google e banners
    const selectors = ['#credential_picker_container', '.nav-header-plus-cp-container', 'iframe[src*="accounts.google.com"]'];
    selectors.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
    
    // Opcional: Esconder o header fixo para o print ficar limpo (melhora muito a visualização)
    const header = document.querySelector('header');
    if(header) header.style.position = 'absolute'; 
    """
    browser.execute_script(script)

def print_function(numero_pagina):
    try:
        remove_popups()
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(2)
        browser.execute_script("window.scrollTo(0, 0);")
        sleep(1)

        produtos = browser.find_elements(By.CSS_SELECTOR, ".ui-search-result__wrapper")
        posicoes_y = sorted(list(set([int(p.location['y']) for p in produtos])))
        
        print(f"Detectadas {len(posicoes_y)} linhas de produtos na página {numero_pagina}.")

        for i in range(len(posicoes_y)):
            y_atual = posicoes_y[i]
            
            if i > 0 and (y_atual > posicoes_y[-2]): 
                break
            browser.execute_script(f"window.scrollTo(0, {y_atual - 10});")
            sleep(0.5)
            
            remove_popups()
            
            nome_arquivo = f"pag{numero_pagina}_linha{i+1}.png"
            caminho_foto = os.path.join(output_dir, nome_arquivo)
            browser.save_screenshot(caminho_foto)
            print(f"Salvo: {nome_arquivo}")

    except Exception as e:
        print(f"Erro: {e}")

for p in range(1, 5):
    print(f"--- Iniciando Página {p} ---")
    print_function(p)
    
    try:
        btn_proximo = browser.find_element(By.CSS_SELECTOR, 'li.andes-pagination__button--next a')
        browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_proximo)
        sleep(1)
        btn_proximo.click()
        sleep(3)
    except:
        print("Fim da navegação.")
        break

browser.quit()