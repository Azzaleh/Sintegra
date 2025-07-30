import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from collections import defaultdict

class SintegraEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Editor Visual de Arquivos SINTEGRA")
        self.root.geometry("1200x800")
        self.root.tk_setPalette(background='#EFEFEF', foreground='#333333')
        
        self.current_file_path = None
        self.sintegra_raw_lines = [] 
        self.sintegra_parsed_data = {} 
        self.current_selected_record_type = None

        self.record_descriptions = {
            "10": "Registro Mestre do Contribuinte: Identificação do estabelecimento.",
            "11": "Dados Complementares do Informante: Endereço e telefone.",
            "50": "Nota Fiscal (modelos 1, 1-A, 4 e NF-e): Operações de entrada e saída.",
            "51": "Valores de IPI e Frete para Notas Fiscais com totalização por item.",
            "53": "Substituição Tributária: Informações sobre ICMS-ST.",
            "54": "Itens da Nota Fiscal: Detalhamento dos produtos/serviços da NF.",
            "60A": "Cupom Fiscal (ECF): Identificação diária dos totalizadores.",
            "61": "Documentos Fiscais não emitidos por ECF (Nota Fiscal de Venda a Consumidor).",
            "70": "Registro referente a Nota Fiscal de Serviço de Transporte e Conhecimento de Transporte.",
            "74": "Registro de Inventário: Informações do estoque ao final do período.",
            "75": "Código de Produto e Serviço: Tabela de cadastro de itens.",
            "90": "Totalizador do Arquivo (Trailer): Verifica a integridade e o total de linhas."
        }


        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10) 

        self.edit_tab = ttk.Frame(self.notebook, padding="10") 
        self.notebook.add(self.edit_tab, text="Visualização / Edição")

        self.totals_tab = ttk.Frame(self.notebook, padding="10") 
        self.notebook.add(self.totals_tab, text="Totais e Resumo")

        left_panel = ttk.Frame(self.edit_tab, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=10)
        left_panel.pack_propagate(False)

        ttk.Label(left_panel, text="ARQUIVO:", font=('Arial', 10, 'bold')).pack(pady=(0,5), anchor=tk.W)
        self.file_label = ttk.Label(left_panel, text="Nenhum arquivo carregado.", wraplength=230)
        self.file_label.pack(pady=5, fill=tk.X)

        load_button = ttk.Button(left_panel, text="Carregar Arquivo SINTEGRA", command=self.load_sintegra_file)
        load_button.pack(pady=10, fill=tk.X)
        
        ttk.Separator(left_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(left_panel, text="TIPOS DE REGISTRO:", font=('Arial', 10, 'bold')).pack(pady=(0,5), anchor=tk.W)
        self.record_type_listbox = tk.Listbox(left_panel, selectmode=tk.SINGLE, height=15, font=('Arial', 10),
                                              bg='#FFFFFF', fg='#333333', selectbackground='#A0D9F0', selectforeground='#000000',
                                              borderwidth=1, relief="solid")
        self.record_type_listbox.pack(pady=5, fill=tk.BOTH, expand=True)
        self.record_type_listbox.bind("<<ListboxSelect>>", self.display_selected_record_type_data)

        right_panel = ttk.Frame(self.edit_tab)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)

        self.current_record_type_label = ttk.Label(right_panel, text="Selecione um tipo de registro para visualizar.", font=('Arial', 12, 'bold'))
        self.current_record_type_label.pack(pady=(10, 0), anchor=tk.W)

        self.record_description_label = ttk.Label(right_panel, text="", font=('Arial', 10, 'italic'), foreground="#555555")
        self.record_description_label.pack(pady=(2, 10), anchor=tk.W)

        tree_frame = ttk.Frame(right_panel)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.data_tree = ttk.Treeview(tree_frame, show="headings")
        self.data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.data_tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.data_tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(right_panel, orient="horizontal", command=self.data_tree.xview)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.data_tree.configure(xscrollcommand=hsb.set)

        self.data_tree.bind("<Double-1>", self.on_cell_double_click)
        
        button_frame = ttk.Frame(right_panel)
        button_frame.pack(pady=10, fill=tk.X, side=tk.BOTTOM)

        save_button = ttk.Button(button_frame, text="Salvar Alterações no Arquivo", command=self.save_sintegra_file)
        save_button.pack(side=tk.RIGHT, padx=5)

        self.setup_totals_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def setup_totals_tab(self):
        # Estrutura de scrollbar
        canvas = tk.Canvas(self.totals_tab, bg='#EFEFEF', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.totals_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(scrollable_frame, text="RESUMO E ANÁLISE DO ARQUIVO SINTEGRA", font=('Arial', 14, 'bold')).pack(pady=15, padx=20)

        # Painéis principais
        main_frame = ttk.Frame(scrollable_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        left_col = ttk.Frame(main_frame)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        right_col = ttk.Frame(main_frame)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Resumo Financeiro com 4 categorias
        financial_frame = ttk.LabelFrame(left_col, text="Resumo Financeiro por Tipo de Operação", padding="10")
        financial_frame.pack(fill=tk.X, pady=5)
        self.totals_entrada_label = ttk.Label(financial_frame, text="TOTAIS DE ENTRADA (NF):", font=('Arial', 10, 'bold'))
        self.totals_entrada_label.pack(anchor=tk.W, pady=(5,0))
        self.total_val_ent_label = ttk.Label(financial_frame, text="  Valor Total: R$ 0,00")
        self.total_val_ent_label.pack(anchor=tk.W)
        self.totals_nfe_saida_label = ttk.Label(financial_frame, text="TOTAIS DE NFe SAÍDA (Mod. 55):", font=('Arial', 10, 'bold'))
        self.totals_nfe_saida_label.pack(anchor=tk.W, pady=(5,0))
        self.total_val_nfe_sai_label = ttk.Label(financial_frame, text="  Valor Total: R$ 0,00")
        self.total_val_nfe_sai_label.pack(anchor=tk.W)
        self.totals_nfce_label = ttk.Label(financial_frame, text="TOTAIS DE NFCe (Mod. 65):", font=('Arial', 10, 'bold'))
        self.totals_nfce_label.pack(anchor=tk.W, pady=(5,0))
        self.total_val_nfce_label = ttk.Label(financial_frame, text="  Valor Total: R$ 0,00")
        self.total_val_nfce_label.pack(anchor=tk.W)
        self.totals_outras_saidas_label = ttk.Label(financial_frame, text="TOTAIS DE OUTRAS SAÍDAS:", font=('Arial', 10, 'bold'))
        self.totals_outras_saidas_label.pack(anchor=tk.W, pady=(5,0))
        self.total_val_outras_sai_label = ttk.Label(financial_frame, text="  Valor Total: R$ 0,00")
        self.total_val_outras_sai_label.pack(anchor=tk.W)

        # Treeview de CFOP com colunas para cada tipo de operação
        cfop_frame = ttk.LabelFrame(left_col, text="Totalizadores por CFOP", padding="10")
        cfop_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.cfop_detailed_tree = ttk.Treeview(cfop_frame, columns=("CFOP", "Entrada", "NFe Saída", "NFCe", "Outras Saídas"), show="headings", height=12)
        self.cfop_detailed_tree.heading("CFOP", text="CFOP"); self.cfop_detailed_tree.column("CFOP", width=60, anchor=tk.CENTER)
        self.cfop_detailed_tree.heading("Entrada", text="Entrada (NF)"); self.cfop_detailed_tree.column("Entrada", width=110, anchor=tk.E)
        self.cfop_detailed_tree.heading("NFe Saída", text="NFe Saída (55)"); self.cfop_detailed_tree.column("NFe Saída", width=110, anchor=tk.E)
        self.cfop_detailed_tree.heading("NFCe", text="NFC-e (65)"); self.cfop_detailed_tree.column("NFCe", width=110, anchor=tk.E)
        self.cfop_detailed_tree.heading("Outras Saídas", text="Outras Saídas"); self.cfop_detailed_tree.column("Outras Saídas", width=110, anchor=tk.E)
        self.cfop_detailed_tree.pack(fill=tk.BOTH, expand=True)

        # =================================================================================
        # CÓDIGO RESTAURADO: Adicionando de volta os widgets da coluna da direita
        # =================================================================================
        cst_frame = ttk.LabelFrame(right_col, text="Totalizadores por CST (Reg. 54)", padding="10")
        cst_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.cst_totals_tree = ttk.Treeview(cst_frame, columns=("CST", "Valor dos Itens", "Base ICMS"), show="headings", height=5)
        self.cst_totals_tree.heading("CST", text="CST"); self.cst_totals_tree.column("CST", width=60, anchor=tk.CENTER)
        self.cst_totals_tree.heading("Valor dos Itens", text="Valor dos Itens"); self.cst_totals_tree.column("Valor dos Itens", width=120, anchor=tk.E)
        self.cst_totals_tree.heading("Base ICMS", text="Base ICMS"); self.cst_totals_tree.column("Base ICMS", width=120, anchor=tk.E)
        self.cst_totals_tree.pack(fill=tk.BOTH, expand=True)

        trailer_frame = ttk.LabelFrame(right_col, text="Validação do Trailer (Registro 90)", padding="10")
        trailer_frame.pack(fill=tk.X, pady=5)
        self.trailer_validation_tree = ttk.Treeview(trailer_frame, columns=("Registro", "Contagem Real", "Declarado (Reg. 90)", "Status"), show="headings", height=5)
        self.trailer_validation_tree.heading("Registro", text="Registro"); self.trailer_validation_tree.column("Registro", width=80, anchor=tk.CENTER)
        self.trailer_validation_tree.heading("Contagem Real", text="Contagem Real"); self.trailer_validation_tree.column("Contagem Real", width=100, anchor=tk.CENTER)
        self.trailer_validation_tree.heading("Declarado (Reg. 90)", text="Declarado (Reg. 90)"); self.trailer_validation_tree.column("Declarado (Reg. 90)", width=120, anchor=tk.CENTER)
        self.trailer_validation_tree.heading("Status", text="Status"); self.trailer_validation_tree.column("Status", width=100, anchor=tk.CENTER)
        self.trailer_validation_tree.pack(fill=tk.BOTH, expand=True)
        
        aliq_frame = ttk.LabelFrame(right_col, text="Totalizadores por Alíquota ICMS (Reg. 50, 54)", padding="10")
        aliq_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.aliq_totals_tree = ttk.Treeview(aliq_frame, columns=("Alíquota", "Base ICMS", "Valor ICMS"), show="headings", height=5)
        self.aliq_totals_tree.heading("Alíquota", text="Alíquota (%)"); self.aliq_totals_tree.column("Alíquota", width=100, anchor=tk.CENTER)
        self.aliq_totals_tree.heading("Base ICMS", text="Base ICMS"); self.aliq_totals_tree.column("Base ICMS", width=120, anchor=tk.E)
        self.aliq_totals_tree.heading("Valor ICMS", text="Valor ICMS"); self.aliq_totals_tree.column("Valor ICMS", width=120, anchor=tk.E)
        self.aliq_totals_tree.pack(fill=tk.BOTH, expand=True)

        # AQUI ESTÁ A PARTE FALTANTE QUE CAUSOU O ERRO
        alerts_frame = ttk.LabelFrame(right_col, text="Alertas e Inconsistências", padding="10")
        alerts_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.alerts_tree = ttk.Treeview(alerts_frame, columns=("Tipo de Alerta", "Detalhes"), show="headings", height=5)
        self.alerts_tree.heading("Tipo de Alerta", text="Tipo de Alerta"); self.alerts_tree.column("Tipo de Alerta", width=150, anchor=tk.W)
        self.alerts_tree.heading("Detalhes", text="Detalhes"); self.alerts_tree.column("Detalhes", width=300, anchor=tk.W)
        self.alerts_tree.pack(fill=tk.BOTH, expand=True)

    
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def _create_register_frame(self, parent, reg_id, title, headers):
        reg_frame = ttk.LabelFrame(parent, text=title, padding="10")
        reg_frame.pack(fill=tk.X, pady=5, anchor=tk.NW)

        for col_idx, header_text in enumerate(headers):
            header_label = ttk.Label(reg_frame, text=header_text, font=('Arial', 9, 'bold'))
            header_label.grid(row=0, column=col_idx + 1, padx=5, pady=(0, 5), sticky=tk.E)

        label_entrada = ttk.Label(reg_frame, text="Entrada", font=('Arial', 10))
        label_entrada.grid(row=1, column=0, padx=5, sticky=tk.W)
        
        label_saida = ttk.Label(reg_frame, text="Saída", font=('Arial', 10))
        label_saida.grid(row=2, column=0, padx=5, sticky=tk.W)

        for op_type, row_idx in [("Entrada", 1), ("Saída", 2)]:
            for col_idx, header_text in enumerate(headers):
                header_key = header_text.lower().replace(" ", "_").replace(".", "").replace("ç", "c").replace("ó", "o").replace("á","a")

                value_label = ttk.Label(reg_frame, text="0,00", font=('Consolas', 10),
                                        padding=(5, 2), relief="solid", borderwidth=1, 
                                        background='white', anchor=tk.E, width=15)
                value_label.grid(row=row_idx, column=col_idx + 1, padx=5, pady=2, sticky=tk.E)
                
                self.summary_labels[reg_id][op_type.lower()][header_key] = value_label

    def print_summary(self):
        messagebox.showinfo("Informação", "Funcionalidade 'Imprimir' ainda não implementada.", parent=self.root)
        print("Botão Imprimir foi clicado.")

    def on_radio_select(self):
        option = self.summary_option.get()
        messagebox.showinfo("Informação", f"Opção '{option}' selecionada.\n\nA lógica para recarregar os dados precisa ser implementada aqui.", parent=self.root)
        print(f"Opção do rádio mudou para: {option}")

    def on_tab_change(self, event):
        selected_tab_index = self.notebook.index(self.notebook.select())
        if self.notebook.tab(selected_tab_index, "text") == "Totais e Resumo":
            self.calculate_and_display_totals()

    def calculate_and_display_totals(self):
        # Limpeza das tabelas
        for tree in [self.cfop_detailed_tree, self.cst_totals_tree, self.aliq_totals_tree, self.trailer_validation_tree]:
            if tree.winfo_exists():
                tree.delete(*tree.get_children())
        if self.alerts_tree.winfo_exists():
            self.alerts_tree.delete(*self.alerts_tree.get_children())

        if not self.sintegra_raw_lines: return

        # Estruturas de dados para armazenar os totais
        totals = {
            'entrada': defaultdict(float),
            'nfe_saida': defaultdict(float),
            'nfce': defaultdict(float),
            'outras_saidas': defaultdict(float)
        }
        cfop_totals = defaultdict(lambda: {
            'entrada': 0.0,
            'nfe_saida': 0.0,
            'nfce': 0.0,
            'outras_saidas': 0.0
        })
        
        cst_totals = defaultdict(lambda: defaultdict(float))
        aliq_totals = defaultdict(lambda: defaultdict(float))
        alerts = []
        reg50_keys = set()
        
        # Pré-processamento do Reg. 50
        if "50" in self.sintegra_parsed_data:
            for line_data in self.sintegra_parsed_data["50"]:
                p = self.parse_line_into_fields("50", self.sintegra_raw_lines[line_data["line_index"]], for_display=False)
                key = (p.get("CNPJ/CPF"), p.get("Modelo"), p.get("Série"), p.get("Número"))
                reg50_keys.add(key)
        
        # Loop principal de cálculo
        for r_type, lines in self.sintegra_parsed_data.items():
            for line_data in lines:
                raw_line = self.sintegra_raw_lines[line_data["line_index"]]
                try:
                    if r_type == "50":
                        p = self.parse_line_into_fields(r_type, raw_line, for_display=False)
                        cfop = p.get("CFOP", "")
                        modelo = p.get("Modelo", "")
                        valor_total = int(p.get("Valor Total NF", 0))
                        base_icms = int(p.get("Base Cálc. ICMS", 0))
                        valor_icms = int(p.get("Valor ICMS", 0))

                        if cfop.startswith(('1', '2', '3')):
                            cat = 'entrada'
                            cfop_totals[cfop][cat] += valor_total
                            totals[cat]['valor_total'] += valor_total
                        elif modelo == '65':
                            cat = 'nfce'
                            cfop_totals[cfop][cat] += valor_total
                            totals[cat]['valor_total'] += valor_total
                        elif modelo == '55':
                            cat = 'nfe_saida'
                            cfop_totals[cfop][cat] += valor_total
                            totals[cat]['valor_total'] += valor_total
                        else:
                            cat = 'outras_saidas'
                            cfop_totals[cfop][cat] += valor_total
                            totals[cat]['valor_total'] += valor_total

                        aliquota = int(p.get("Alíquota", 0))
                        if aliquota > 0 and base_icms > 0:
                            aliq_totals[aliquota]['base_icms'] += base_icms
                            aliq_totals[aliquota]['valor_icms'] += valor_icms

                    elif r_type == "54":
                        p = self.parse_line_into_fields(r_type, raw_line, for_display=False)
                        cst = p.get("CST", ""); valor_item = int(p.get("Valor Item", 0)); base_icms = int(p.get("Base ICMS", 0))
                        cst_totals[cst]['valor_item'] += valor_item; cst_totals[cst]['base_icms'] += base_icms
                        key = (p.get("CNPJ"), p.get("Modelo"), p.get("Série"), p.get("Número NF"))
                        if key not in reg50_keys:
                            alerts.append(("Reg. 54 Órfão", f"Linha {line_data['line_index']+1}: Item de NF não encontrada."))
                    
                    # =================================================================================
                    # ALTERADO: Lógica para o Registro 61
                    # =================================================================================
                    elif r_type == "61":
                        p = self.parse_line_into_fields(r_type, raw_line, for_display=False)
                        valor_total_reg61 = int(p.get("Valor Total", 0))
                        
                        # 1. Adiciona ao resumo geral de "Outras Saídas"
                        totals['outras_saidas']['valor_total'] += valor_total_reg61
                        
                        # 2. NOVO: Adiciona ao detalhamento por CFOP com um código descritivo
                        cfop_placeholder = "61-SAÍDA"
                        cfop_totals[cfop_placeholder]['outras_saidas'] += valor_total_reg61

                except (ValueError, TypeError) as e:
                    alerts.append(("Erro de Leitura", f"Linha {line_data['line_index']+1} (Tipo {r_type}): {e}"))

        # Atualiza os labels de Resumo Financeiro
        self.total_val_ent_label.config(text=f"  Valor Total: {self.format_numeric_value_to_brl(totals['entrada']['valor_total'])}")
        self.total_val_nfe_sai_label.config(text=f"  Valor Total: {self.format_numeric_value_to_brl(totals['nfe_saida']['valor_total'])}")
        self.total_val_nfce_label.config(text=f"  Valor Total: {self.format_numeric_value_to_brl(totals['nfce']['valor_total'])}")
        self.total_val_outras_sai_label.config(text=f"  Valor Total: {self.format_numeric_value_to_brl(totals['outras_saidas']['valor_total'])}")

        # Preenche a Treeview de CFOPs detalhados
        for cfop, data in sorted(cfop_totals.items()):
            if any(data.values()):
                self.cfop_detailed_tree.insert("", tk.END, values=(
                    cfop,
                    self.format_numeric_value_to_brl(data['entrada']),
                    self.format_numeric_value_to_brl(data['nfe_saida']),
                    self.format_numeric_value_to_brl(data['nfce']),
                    self.format_numeric_value_to_brl(data['outras_saidas'])
                ))
        
        # Preenche as outras tabelas
        for cst, data in sorted(cst_totals.items()): self.cst_totals_tree.insert("", tk.END, values=(cst, self.format_numeric_value_to_brl(data['valor_item']), self.format_numeric_value_to_brl(data['base_icms'])))
        for aliquota, data in sorted(aliq_totals.items()): self.aliq_totals_tree.insert("", tk.END, values=(f"{aliquota/100:.2f}%", self.format_numeric_value_to_brl(data['base_icms']), self.format_numeric_value_to_brl(data['valor_icms'])))
        
        self.validate_trailer()
        for alert_type, detail in alerts: self.alerts_tree.insert("", tk.END, values=(alert_type, detail))

    def validate_trailer(self):
        if "90" not in self.sintegra_parsed_data:
            self.trailer_validation_tree.insert("", tk.END, values=("90", "N/A", "N/A", "Não Encontrado"), tags=("DIVERGÊNCIA",))
            return
            
        trailer_line = self.sintegra_raw_lines[self.sintegra_parsed_data["90"][0]["line_index"]]
        trailer_counts = {}
        pos = 30
        while pos < 118:
            r_type = trailer_line[pos:pos+2]
            if not r_type.strip() or not r_type.isdigit(): break
            count = int(trailer_line[pos+2:pos+10])
            trailer_counts[r_type] = count
            pos += 10
            
        total_geral_trailer = int(trailer_line[118:126])
        total_geral_real = len(self.sintegra_raw_lines)
        all_record_types = set(self.sintegra_parsed_data.keys()) | set(trailer_counts.keys())
        
        for r_type in sorted(list(all_record_types)):
            if r_type == '90': continue # O registro 90 não totaliza a si mesmo
            real_count = len(self.sintegra_parsed_data.get(r_type, []))
            trailer_count = trailer_counts.get(r_type, 0)
            status = "OK" if real_count == trailer_count else "DIVERGÊNCIA"
            self.trailer_validation_tree.insert("", tk.END, values=(r_type, real_count, trailer_count, status), tags=(status,))
            
        status_geral = "OK" if total_geral_real == total_geral_trailer else "DIVERGÊNCIA"
        self.trailer_validation_tree.insert("", tk.END, values=("TOTAL LINHAS", total_geral_real, total_geral_trailer, status_geral), tags=(status_geral,))
        
        self.trailer_validation_tree.tag_configure("DIVERGÊNCIA", background="#FFDDDD", foreground="black")
        self.trailer_validation_tree.tag_configure("OK", background="#DDFFAA", foreground="black")

    def _update_summary_display(self, reg_id, totals_data):
        for op_type in ['entrada', 'saida']:
            if op_type in totals_data:
                for field, value in totals_data[op_type].items():
                    if field in self.summary_labels[reg_id][op_type]:
                        formatted_value = self.format_numeric_value_to_brl(value, include_rs=False)
                        self.summary_labels[reg_id][op_type][field].config(text=formatted_value)

    def apply_styles(self):
        self.style = ttk.Style(); self.style.theme_use('clam') 
        self.style.configure('TFrame', background='#EFEFEF'); self.style.configure('TLabel', background='#EFEFEF', font=('Arial', 10))
        self.style.configure('TButton', font=('Arial', 10, 'bold'), padding=5); self.style.configure('Treeview.Heading', font=('Arial', 10, 'bold'), background='#007ACC', foreground='#FFFFFF')
        self.style.configure('Treeview', font=('Consolas', 9), rowheight=22, background='#FFFFFF', foreground='#333333', fieldbackground='#FFFFFF')
        self.style.configure('TLabelframe.Label', font=('Arial', 11, 'bold'), background='#EFEFEF')
        self.data_tree.tag_configure('oddrow', background='#F8F8F8'); self.data_tree.tag_configure('evenrow', background='#E8E8E8')

    def load_sintegra_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")])
        if file_path:
            self.current_file_path = file_path; self.file_label.config(text=f"{os.path.basename(file_path)}")
            self.parse_sintegra_file(); self.populate_record_type_listbox(); self.notebook.select(self.edit_tab)
            messagebox.showinfo("Sucesso", "Arquivo SINTEGRA carregado!\n\nAcesse a aba 'Totais e Resumo' para ver a análise completa.")

    def parse_sintegra_file(self):
        self.sintegra_raw_lines = []; self.sintegra_parsed_data = defaultdict(list)
        try:
            with open(self.current_file_path, 'r', encoding='latin-1') as f:
                for line_num, line in enumerate(f):
                    cleaned_line = line.rstrip('\r\n')
                    if not cleaned_line.strip(): continue
                    cleaned_line = cleaned_line.ljust(126, ' ')[:126] 
                    self.sintegra_raw_lines.append(cleaned_line)
                    self.sintegra_parsed_data[cleaned_line[0:2]].append({"line_index": len(self.sintegra_raw_lines) - 1})
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao ler o arquivo: {e}")
            self.current_file_path = None; self.file_label.config(text="Erro ao carregar arquivo.")
            self.record_type_listbox.delete(0, tk.END)

    def parse_line_into_fields(self, record_type, line_content, for_display=True):
        fields_def = self.get_record_fields_info(record_type); parsed_fields = {}
        if fields_def:
            for field_def in fields_def:
                start_pos, end_pos = field_def["start"] - 1, field_def["end"]
                raw_field_val = line_content[start_pos:end_pos]
                if for_display and field_def["format"] == "N" and "Valor" in field_def["name"] and field_def["size"] >= 4:
                    parsed_fields[field_def["name"]] = self.format_numeric_value_to_brl(raw_field_val)
                else:
                    parsed_fields[field_def["name"]] = raw_field_val.strip()
        return parsed_fields

    def populate_record_type_listbox(self):
        self.record_type_listbox.delete(0, tk.END)
        for r_type in sorted(self.sintegra_parsed_data.keys()):
            self.record_type_listbox.insert(tk.END, f"{r_type} ({len(self.sintegra_parsed_data[r_type])} regs)")

    def display_selected_record_type_data(self, event):
        selected_indices = self.record_type_listbox.curselection()
        if not selected_indices: return

        selected_item = self.record_type_listbox.get(selected_indices[0])
        selected_record_type = selected_item.split(" ")[0]
        self.current_selected_record_type = selected_record_type
        
        self.current_record_type_label.config(text=f"REGISTRO {selected_record_type} - Detalhes e Edição")
        description = self.record_descriptions.get(selected_record_type, "Descrição não disponível.")
        if selected_record_type.startswith("60"): description = self.record_descriptions.get("60", "Descrição não disponível.")
        self.record_description_label.config(text=description)

        self.clear_data_tree()
        fields_def = self.get_record_fields_info(selected_record_type)
        if not fields_def:
            self.data_tree["columns"] = ("Linha Completa",); self.data_tree.heading("Linha Completa", text="Conteúdo da Linha (Layout não definido)")
            self.data_tree.column("Linha Completa", width=1000, anchor=tk.W)
            for i, line_data in enumerate(self.sintegra_parsed_data[selected_record_type]):
                self.data_tree.insert("", tk.END, iid=line_data["line_index"], values=(self.sintegra_raw_lines[line_data["line_index"]],), tags=('oddrow' if i % 2 else 'evenrow',))
            return

        column_names = [f_def["name"] for f_def in fields_def]
        self.data_tree["columns"] = column_names
        
        for f_def in fields_def:
            width = max(len(f_def["name"]) * 8, f_def["size"] * 7, 70)
            self.data_tree.heading(f_def["name"], text=f_def["name"]); self.data_tree.column(f_def["name"], width=width + 15, anchor=tk.W)

        for i, line_data in enumerate(self.sintegra_parsed_data[selected_record_type]):
            values = list(self.parse_line_into_fields(selected_record_type, self.sintegra_raw_lines[line_data["line_index"]], for_display=True).values())
            self.data_tree.insert("", tk.END, iid=line_data["line_index"], values=values, tags=('oddrow' if i % 2 else 'evenrow',))

    def get_record_fields_info(self, record_type):
        # ADICIONADO LAYOUTS FALTANTES (51, 53, 61) PARA COMPLETUDE DOS CÁLCULOS
        fields_info = {
            "10": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Inscrição Estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Nome do Contribuinte", "size": 35, "start": 31, "end": 65, "format": "X"}, {"name": "Município", "size": 30, "start": 66, "end": 95, "format": "X"}, {"name": "UF", "size": 2, "start": 96, "end": 97, "format": "X"}, {"name": "Fax", "size": 10, "start": 98, "end": 107, "format": "N"}, {"name": "Data Inicial", "size": 8, "start": 108, "end": 115, "format": "N"}, {"name": "Data Final", "size": 8, "start": 116, "end": 123, "format": "N"}, {"name": "Cod. Estrutura", "size": 1, "start": 124, "end": 124, "format": "X"}, {"name": "Cod. Operações", "size": 1, "start": 125, "end": 125, "format": "X"}, {"name": "Cod. Finalidade", "size": 1, "start": 126, "end": 126, "format": "X"} ],
            "11": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "Logradouro", "size": 34, "start": 3, "end": 36, "format": "X"}, {"name": "Número", "size": 5, "start": 37, "end": 41, "format": "N"}, {"name": "Complemento", "size": 22, "start": 42, "end": 63, "format": "X"}, {"name": "Bairro", "size": 15, "start": 64, "end": 78, "format": "X"}, {"name": "CEP", "size": 8, "start": 79, "end": 86, "format": "N"}, {"name": "Nome Contato", "size": 28, "start": 87, "end": 114, "format": "X"}, {"name": "Telefone", "size": 12, "start": 115, "end": 126, "format": "N"} ],
            "50": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ/CPF", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Insc. Estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Data Emissão/Rec.", "size": 8, "start": 31, "end": 38, "format": "N"}, {"name": "UF", "size": 2, "start": 39, "end": 40, "format": "X"}, {"name": "Modelo", "size": 2, "start": 41, "end": 42, "format": "N"}, {"name": "Série", "size": 3, "start": 43, "end": 45, "format": "X"}, {"name": "Número", "size": 6, "start": 46, "end": 51, "format": "N"}, {"name": "CFOP", "size": 4, "start": 52, "end": 55, "format": "N"}, {"name": "Emitente", "size": 1, "start": 56, "end": 56, "format": "X"}, {"name": "Valor Total NF", "size": 13, "start": 57, "end": 69, "format": "N"}, {"name": "Base Cálc. ICMS", "size": 13, "start": 70, "end": 82, "format": "N"}, {"name": "Valor ICMS", "size": 13, "start": 83, "end": 95, "format": "N"}, {"name": "Isenta/Não Trib.", "size": 13, "start": 96, "end": 108, "format": "N"}, {"name": "Outras", "size": 13, "start": 109, "end": 121, "format": "N"}, {"name": "Alíquota", "size": 4, "start": 122, "end": 125, "format": "N"}, {"name": "Situação", "size": 1, "start": 126, "end": 126, "format": "X"} ],
            "51": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ/CPF", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Insc. Estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Data Emissão/Rec.", "size": 8, "start": 31, "end": 38, "format": "N"}, {"name": "UF", "size": 2, "start": 39, "end": 40, "format": "X"}, {"name": "Modelo", "size": 2, "start": 41, "end": 42, "format": "N"}, {"name": "Série", "size": 3, "start": 43, "end": 45, "format": "X"}, {"name": "Número", "size": 6, "start": 46, "end": 51, "format": "N"}, {"name": "CFOP", "size": 4, "start": 52, "end": 55, "format": "N"}, {"name": "Valor IPI", "size": 13, "start": 56, "end": 68, "format": "N"}, {"name": "Valor Frete", "size": 13, "start": 69, "end": 81, "format": "N"}, {"name": "Brancos", "size": 45, "start": 82, "end": 126, "format": "X"} ],
            "53": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ/CPF", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Insc. Estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Data Emissão/Rec.", "size": 8, "start": 31, "end": 38, "format": "N"}, {"name": "UF", "size": 2, "start": 39, "end": 40, "format": "X"}, {"name": "Modelo", "size": 2, "start": 41, "end": 42, "format": "N"}, {"name": "Série", "size": 3, "start": 43, "end": 45, "format": "X"}, {"name": "Número", "size": 6, "start": 46, "end": 51, "format": "N"}, {"name": "CFOP", "size": 4, "start": 52, "end": 55, "format": "N"}, {"name": "Base ICMS ST", "size": 13, "start": 56, "end": 68, "format": "N"}, {"name": "Valor ICMS Retido", "size": 13, "start": 69, "end": 81, "format": "N"}, {"name": "Despesas Acessórias", "size": 13, "start": 82, "end": 94, "format": "N"}, {"name": "Situação", "size": 1, "start": 95, "end": 95, "format": "X"}, {"name": "Brancos", "size": 31, "start": 96, "end": 126, "format": "X"} ],
            "54": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Modelo", "size": 2, "start": 17, "end": 18, "format": "N"}, {"name": "Série", "size": 3, "start": 19, "end": 21, "format": "X"}, {"name": "Número NF", "size": 6, "start": 22, "end": 27, "format": "N"}, {"name": "CFOP", "size": 4, "start": 28, "end": 31, "format": "N"}, {"name": "CST", "size": 3, "start": 32, "end": 34, "format": "X"}, {"name": "Nº Item", "size": 3, "start": 35, "end": 37, "format": "N"}, {"name": "Cód. Produto", "size": 14, "start": 38, "end": 51, "format": "X"}, {"name": "Quantidade", "size": 11, "start": 52, "end": 62, "format": "N"}, {"name": "Valor Item", "size": 12, "start": 63, "end": 74, "format": "N"}, {"name": "Valor Desconto", "size": 12, "start": 75, "end": 86, "format": "N"}, {"name": "Base ICMS", "size": 12, "start": 87, "end": 98, "format": "N"}, {"name": "Base ICMS ST", "size": 12, "start": 99, "end": 110, "format": "N"}, {"name": "Valor IPI", "size": 12, "start": 111, "end": 122, "format": "N"}, {"name": "Alíquota ICMS", "size": 4, "start": 123, "end": 126, "format": "N"} ],
            "61": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "Brancos", "size": 10, "start": 3, "end": 12, "format": "X"}, {"name": "Data Emissão", "size": 8, "start": 13, "end": 20, "format": "N"}, {"name": "Modelo", "size": 2, "start": 21, "end": 22, "format": "N"}, {"name": "Série", "size": 3, "start": 23, "end": 25, "format": "X"}, {"name": "SubSérie", "size": 2, "start": 26, "end": 27, "format": "X"}, {"name": "Nº Inicial", "size": 6, "start": 28, "end": 33, "format": "N"}, {"name": "Nº Final", "size": 6, "start": 34, "end": 39, "format": "N"}, {"name": "Valor Total", "size": 13, "start": 40, "end": 52, "format": "N"}, {"name": "Base Cálc. ICMS", "size": 13, "start": 53, "end": 65, "format": "N"}, {"name": "Valor ICMS", "size": 13, "start": 66, "end": 78, "format": "N"}, {"name": "Isenta/Não Trib.", "size": 13, "start": 79, "end": 91, "format": "N"}, {"name": "Outras", "size": 13, "start": 92, "end": 104, "format": "N"}, {"name": "Alíquota", "size": 4, "start": 105, "end": 108, "format": "N"}, {"name": "Brancos", "size": 18, "start": 109, "end": 126, "format": "X"}],
            "75": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "Data Inicial", "size": 8, "start": 3, "end": 10, "format": "N"}, {"name": "Data Final", "size": 8, "start": 11, "end": 18, "format": "N"}, {"name": "Cód. Produto", "size": 14, "start": 19, "end": 32, "format": "X"}, {"name": "Cód. NCM", "size": 8, "start": 33, "end": 40, "format": "N"}, {"name": "Descrição", "size": 53, "start": 41, "end": 93, "format": "X"}, {"name": "Unidade Medida", "size": 6, "start": 94, "end": 99, "format": "X"}, {"name": "Alíquota IPI", "size": 4, "start": 100, "end": 103, "format": "N"}, {"name": "Alíquota ICMS", "size": 4, "start": 104, "end": 107, "format": "N"}, {"name": "Red. Base ICMS", "size": 5, "start": 108, "end": 112, "format": "N"}, {"name": "Base ICMS ST", "size": 5, "start": 113, "end": 117, "format": "N"}, {"name": "Branco", "size": 9, "start": 118, "end": 126, "format": "X"} ],
        }
        return fields_info.get(record_type, None)

    def clear_data_tree(self):
        self.data_tree.delete(*self.data_tree.get_children()); self.data_tree["columns"] = []

    def on_cell_double_click(self, event):
        region = self.data_tree.identify_region(event.x, event.y)
        if region == "heading": return
        item_id = self.data_tree.identify_row(event.y); col_id = self.data_tree.identify_column(event.x)
        if not item_id or not col_id: return
        if not self.get_record_fields_info(self.current_selected_record_type):
            messagebox.showinfo("Informação", "A edição não está disponível para registros com layout não definido."); return
        column_index = int(col_id.replace('#', '')) - 1; column_name = self.data_tree['columns'][column_index]
        fields_def = self.get_record_fields_info(self.current_selected_record_type)
        field_info = next((f for f in fields_def if f["name"] == column_name), None)
        if not field_info: return
        raw_line_content = self.sintegra_raw_lines[int(item_id)]; start_pos_0_based = field_info["start"] - 1
        original_raw_value = raw_line_content[start_pos_0_based:field_info["end"]]
        if field_info["format"] == "N" and "Valor" in field_info["name"] and field_info["size"] >= 4:
            value_for_editor = self.format_numeric_value_to_brl(original_raw_value, include_rs=False)
        else: value_for_editor = original_raw_value.strip()
        editor = FieldEditorDialog(self.root, column_name, value_for_editor, field_info["size"], field_info["start"], field_info["end"], field_info["format"], is_monetary="Valor" in field_info["name"] and field_info["format"] == "N")
        self.root.wait_window(editor.top)
        if editor.new_value_for_raw_line is not None:
            current_values_list = list(self.data_tree.item(item_id, 'values')); current_values_list[column_index] = editor.new_value_for_display
            self.data_tree.item(item_id, values=current_values_list); self.update_raw_sintegra_line_content(int(item_id), field_info, editor.new_value_for_raw_line)

    def update_raw_sintegra_line_content(self, line_index, field_info, formatted_new_value):
        original_line_chars = list(self.sintegra_raw_lines[line_index]); start_pos_0_based = field_info["start"] - 1
        for i, char in enumerate(formatted_new_value):
            if start_pos_0_based + i < len(original_line_chars): original_line_chars[start_pos_0_based + i] = char
        self.sintegra_raw_lines[line_index] = "".join(original_line_chars).ljust(126, ' ')[:126]

    def format_numeric_value_to_brl(self, raw_value, include_rs=True):
        try:
            if isinstance(raw_value, (int, float)): clean_value = raw_value
            else: clean_value = int(''.join(filter(str.isdigit, str(raw_value))))
            float_value = clean_value / 100.0
            formatted = f"{float_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {formatted}" if include_rs else formatted
        except (ValueError, TypeError): return "R$ 0,00" if include_rs else "0,00"

    def save_sintegra_file(self):
        if not self.current_file_path: messagebox.showwarning("Aviso", "Nenhum arquivo para salvar."); return
        save_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")], initialfile=os.path.basename(self.current_file_path).replace(".txt", "_EDITADO.txt"))
        if not save_path: return
        try:
            with open(save_path, 'w', encoding='latin-1', newline='\r\n') as f: f.write("\r\n".join(self.sintegra_raw_lines))
            messagebox.showinfo("Sucesso", f"Arquivo salvo com sucesso em: {save_path}")
        except Exception as e: messagebox.showerror("Erro", f"Erro ao salvar o arquivo: {e}")

class FieldEditorDialog:
    def __init__(self, parent, field_name, current_value_for_editor, field_size, field_start, field_end, field_format, is_monetary=False):
        self.new_value_for_raw_line = None; self.new_value_for_display = None   
        self.top = tk.Toplevel(parent); self.top.title(f"Editar Campo: {field_name}"); self.top.geometry("450x240"); self.top.transient(parent); self.top.grab_set()
        ttk.Label(self.top, text=f"Campo: {field_name}", font=('Arial', 11, 'bold')).pack(pady=(10,5))
        ttk.Label(self.top, text=f"Tamanho Máximo: {field_size} caracteres | Posições: {field_start}-{field_end}").pack(pady=2)
        ttk.Label(self.top, text=f"Formato: {'Numérico' if field_format == 'N' else 'Alfanumérico'}").pack(pady=2)
        if is_monetary: ttk.Label(self.top, text="Insira o valor em R$ (ex: 71,50)", font=('Arial', 9, 'italic'), foreground='blue').pack(pady=2)
        self.entry = ttk.Entry(self.top, width=60, font=('Consolas', 10)); self.entry.insert(0, str(current_value_for_editor)); self.entry.pack(pady=10, padx=10); self.entry.focus_set()
        self.field_size, self.field_format, self.is_monetary = field_size, field_format, is_monetary
        button_frame = ttk.Frame(self.top); button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Salvar", command=self.save_and_close).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancelar", command=self.top.destroy).pack(side=tk.RIGHT, padx=10)
        self.top.bind('<Return>', lambda e: self.save_and_close()); self.top.bind('<Escape>', lambda e: self.top.destroy())
    def save_and_close(self):
        entered_value = self.entry.get()
        if self.is_monetary:
            cleaned_monetary_input = entered_value.replace("R$", "").strip().replace(".", "").replace(",", "")
            try:
                if not cleaned_monetary_input: cleaned_monetary_input = '0'
                int_val = int(cleaned_monetary_input)
                if len(str(int_val)) > self.field_size: messagebox.showwarning("Erro", f"Valor excede o tamanho máximo ({self.field_size} dígitos).", parent=self.top); return
                self.new_value_for_raw_line = str(int_val).rjust(self.field_size, '0')
                self.new_value_for_display = self.format_display_brl(int_val)
            except ValueError: messagebox.showwarning("Erro", "Valor monetário inválido.", parent=self.top); return
        else: 
            if len(entered_value) > self.field_size: messagebox.showwarning("Erro", f"Valor excede o tamanho máximo ({self.field_size} caracteres).", parent=self.top); return
            if self.field_format == "N" and not entered_value.isdigit() and entered_value: messagebox.showwarning("Erro", "Campo numérico, insira apenas dígitos.", parent=self.top); return
            self.new_value_for_raw_line = entered_value.ljust(self.field_size, ' ') if self.field_format == "X" else entered_value.rjust(self.field_size, '0')
            self.new_value_for_display = entered_value.strip()
        self.top.destroy()
    def format_display_brl(self, int_value):
        float_value = int_value / 100.0
        return f"R$ {float_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

if __name__ == "__main__":
    root = tk.Tk()
    app = SintegraEditorApp(root)
    root.mainloop()