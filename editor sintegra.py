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
            "61": "Documentos Fiscais não emitidos por ECF (Nota Fiscal de Venda a Consumidor - Modelo 2).", 
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

        search_frame = ttk.Frame(right_panel)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="Pesquisar por Nº NF:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        
        self.search_button = ttk.Button(search_frame, text="Pesquisar", command=self.search_nf_number)
        self.search_button.pack(side=tk.LEFT, padx=5)

        self.clear_search_button = ttk.Button(search_frame, text="Limpar", command=self.clear_search)
        self.clear_search_button.pack(side=tk.LEFT, padx=5)

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
        
        self.toggle_search_fields(False)

        self.setup_totals_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def toggle_search_fields(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.search_entry.config(state=state)
        self.search_button.config(state=state)
        self.clear_search_button.config(state=state)

    def search_nf_number(self):
        search_term = self.search_entry.get().strip()
        if not search_term or not self.current_selected_record_type: return

        self.data_tree.delete(*self.data_tree.get_children())
        fields_def = self.get_record_fields_info(self.current_selected_record_type)
        if not fields_def: return

        nf_col_name = next((f["name"] for f in fields_def if f["name"] in ["Número", "Número NF", "Número inicial"]), None)
        if not nf_col_name: return

        i = 0
        for line_data in self.sintegra_parsed_data.get(self.current_selected_record_type, []):
            line_content = self.sintegra_raw_lines[line_data["line_index"]]
            parsed_fields = self.parse_line_into_fields(self.current_selected_record_type, line_content, for_display=True)
            
            nf_value = parsed_fields.get(nf_col_name, "").lstrip('0')
            if nf_value == search_term.lstrip('0'):
                values = list(parsed_fields.values())
                self.data_tree.insert("", tk.END, iid=line_data["line_index"], values=values, tags=('oddrow' if i % 2 else 'evenrow',))
                i += 1

    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.display_selected_record_type_data(None)

    def setup_totals_tab(self):
        canvas = tk.Canvas(self.totals_tab, bg='#EFEFEF', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.totals_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Label(scrollable_frame, text="ANÁLISE DETALHADA DO ARQUIVO SINTEGRA", font=('Arial', 14, 'bold')).pack(pady=15, padx=20)
        
        info_frame = ttk.LabelFrame(scrollable_frame, text="Informações Gerais do Arquivo", padding="10")
        info_frame.pack(fill=tk.X, pady=5, padx=20)
        self.info_cnpj_label = ttk.Label(info_frame, text="CNPJ do Informante: Não Carregado")
        self.info_cnpj_label.pack(anchor=tk.W, pady=2)
        self.info_ie_label = ttk.Label(info_frame, text="Inscrição Estadual: Não Carregada")
        self.info_ie_label.pack(anchor=tk.W, pady=2)
        self.info_periodo_label = ttk.Label(info_frame, text="Período de Referência: Não Carregado")
        self.info_periodo_label.pack(anchor=tk.W, pady=2)
        self.info_total_linhas_label = ttk.Label(info_frame, text="Total de Linhas no Arquivo: 0")
        self.info_total_linhas_label.pack(anchor=tk.W, pady=2)

        reg_count_frame = ttk.LabelFrame(scrollable_frame, text="Contagem de Registros por Tipo e Validação (Reg. 90)", padding="10")
        reg_count_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=20)
        self.reg_count_tree = ttk.Treeview(reg_count_frame, columns=("Registro", "Descrição", "Contagem Real", "Declarado (Reg. 90)", "Status"), show="headings", height=8)
        self.reg_count_tree.heading("Registro", text="Registro"); self.reg_count_tree.column("Registro", width=70, anchor=tk.CENTER)
        self.reg_count_tree.heading("Descrição", text="Descrição"); self.reg_count_tree.column("Descrição", width=250, anchor=tk.W)
        self.reg_count_tree.heading("Contagem Real", text="Contagem Real"); self.reg_count_tree.column("Contagem Real", width=120, anchor=tk.CENTER)
        self.reg_count_tree.heading("Declarado (Reg. 90)", text="Declarado (Reg. 90)"); self.reg_count_tree.column("Declarado (Reg. 90)", width=150, anchor=tk.CENTER)
        self.reg_count_tree.heading("Status", text="Status"); self.reg_count_tree.column("Status", width=80, anchor=tk.CENTER)
        self.reg_count_tree.pack(fill=tk.BOTH, expand=True)

        financial_frame = ttk.LabelFrame(scrollable_frame, text="Resumo Financeiro por Tipo de Operação", padding="10")
        financial_frame.pack(fill=tk.X, pady=10, padx=20)
        self.totals_entrada_label = ttk.Label(financial_frame, text="TOTAIS DE ENTRADA (NF): R$ 0,00", font=('Arial', 10, 'bold'))
        self.totals_entrada_label.pack(anchor=tk.W, pady=(5,0))
        self.totals_nfe_saida_label = ttk.Label(financial_frame, text="TOTAIS DE SAÍDA (NF-e Mod. 55): R$ 0,00", font=('Arial', 10, 'bold'))
        self.totals_nfe_saida_label.pack(anchor=tk.W, pady=(5,0))
        self.totals_reg61_label = ttk.Label(financial_frame, text="TOTAIS DE SAÍDA (Consumidor Mod. 02): R$ 0,00", font=('Arial', 10, 'bold'))
        self.totals_reg61_label.pack(anchor=tk.W, pady=(5,0))
        self.totals_outras_saidas_label = ttk.Label(financial_frame, text="TOTAIS DE OUTRAS SAÍDAS (NF): R$ 0,00", font=('Arial', 10, 'bold'))
        self.totals_outras_saidas_label.pack(anchor=tk.W, pady=(5,0))

        cfop_frame = ttk.LabelFrame(scrollable_frame, text="Totalizadores por CFOP", padding="10")
        cfop_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=20)
        self.cfop_detailed_tree = ttk.Treeview(cfop_frame, columns=("CFOP", "Entrada", "Saída"), show="headings", height=10)
        self.cfop_detailed_tree.heading("CFOP", text="CFOP"); self.cfop_detailed_tree.column("CFOP", width=70, anchor=tk.CENTER)
        self.cfop_detailed_tree.heading("Entrada", text="Valor Entrada"); self.cfop_detailed_tree.column("Entrada", width=120, anchor=tk.E)
        self.cfop_detailed_tree.heading("Saída", text="Valor Saída"); self.cfop_detailed_tree.column("Saída", width=120, anchor=tk.E)
        self.cfop_detailed_tree.pack(fill=tk.BOTH, expand=True)

        icms_detail_frame = ttk.LabelFrame(scrollable_frame, text="Detalhamento de ICMS", padding="10")
        icms_detail_frame.pack(fill=tk.X, pady=10, padx=20)
        ttk.Label(icms_detail_frame, text="Totais por CST (Reg. 54):", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5,2))
        self.cst_totals_tree = ttk.Treeview(icms_detail_frame, columns=("CST", "Valor dos Itens", "Base ICMS"), show="headings", height=5)
        self.cst_totals_tree.heading("CST", text="CST"); self.cst_totals_tree.column("CST", width=70, anchor=tk.CENTER)
        self.cst_totals_tree.heading("Valor dos Itens", text="Valor dos Itens"); self.cst_totals_tree.column("Valor dos Itens", width=150, anchor=tk.E)
        self.cst_totals_tree.heading("Base ICMS", text="Base ICMS"); self.cst_totals_tree.column("Base ICMS", width=150, anchor=tk.E)
        self.cst_totals_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(icms_detail_frame, text="Totais por Alíquota ICMS (Reg. 50 e 61):", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5,2))
        self.aliq_totals_tree = ttk.Treeview(icms_detail_frame, columns=("Alíquota", "Base ICMS", "Valor ICMS"), show="headings", height=5)
        self.aliq_totals_tree.heading("Alíquota", text="Alíquota (%)"); self.aliq_totals_tree.column("Alíquota", width=100, anchor=tk.CENTER)
        self.aliq_totals_tree.heading("Base ICMS", text="Base ICMS"); self.aliq_totals_tree.column("Base ICMS", width=150, anchor=tk.E)
        self.aliq_totals_tree.heading("Valor ICMS", text="Valor ICMS"); self.aliq_totals_tree.column("Valor ICMS", width=150, anchor=tk.E)
        self.aliq_totals_tree.pack(fill=tk.BOTH, expand=True)

    def on_tab_change(self, event):
        selected_tab_text = self.notebook.tab(self.notebook.select(), "text")
        if selected_tab_text == "Totais e Resumo":
            self.calculate_and_display_totals()

    def calculate_and_display_totals(self):
        for tree in [self.reg_count_tree, self.cfop_detailed_tree, self.cst_totals_tree, self.aliq_totals_tree]:
            if tree.winfo_exists(): tree.delete(*tree.get_children())
        
        if not self.sintegra_raw_lines: return
        
        totals = defaultdict(int)
        cfop_totals = defaultdict(lambda: defaultdict(int))
        cst_totals = defaultdict(lambda: defaultdict(int))
        aliq_totals = defaultdict(lambda: defaultdict(int))

        for r_type, lines in self.sintegra_parsed_data.items():
            for line_data in lines:
                try: # Adicionado para robustez
                    raw_line = self.sintegra_raw_lines[line_data["line_index"]]
                    p = self.parse_line_into_fields(r_type, raw_line, for_display=False)

                    if r_type == "50":
                        cfop = p.get("CFOP", "").strip()
                        modelo = p.get("Modelo", "").strip()
                        valor_total = int(p.get("Valor Total NF", "0"))
                        base_icms = int(p.get("Base Cálc. ICMS", "0"))
                        valor_icms = int(p.get("Valor ICMS", "0"))
                        aliq = int(p.get("Alíquota", "0"))

                        if cfop.startswith(('1', '2', '3')):
                            totals['entrada'] += valor_total
                            cfop_totals[cfop]['entrada'] += valor_total
                        elif cfop.startswith(('5', '6', '7')):
                            if modelo == '55':
                                totals['saida_nfe'] += valor_total
                            else:
                                totals['outras_saidas'] += valor_total
                            cfop_totals[cfop]['saida'] += valor_total
                        
                        if aliq > 0:
                            aliq_totals[aliq]['base_icms'] += base_icms
                            aliq_totals[aliq]['valor_icms'] += valor_icms
                    
                    elif r_type == "54":
                        cst = p.get("CST", "").strip()
                        valor_item = int(p.get("Valor Item", "0"))
                        base_icms = int(p.get("Base ICMS", "0"))
                        cst_totals[cst]['valor_item'] += valor_item
                        cst_totals[cst]['base_icms'] += base_icms
                    
                    elif r_type == "61":
                        valor_total = int(p.get("Valor total", "0"))
                        base_icms = int(p.get("Base de cálculo ICMS", "0"))
                        valor_icms = int(p.get("Valor do ICMS", "0"))
                        aliq = int(p.get("Alíquota", "0"))
                        
                        totals['saida_reg61'] += valor_total
                        if aliq > 0:
                            aliq_totals[aliq]['base_icms'] += base_icms
                            aliq_totals[aliq]['valor_icms'] += valor_icms
                except (ValueError, IndexError, TypeError):
                    # Ignora linhas mal formatadas para não quebrar a sumarização
                    continue

        self.totals_entrada_label.config(text=f"TOTAIS DE ENTRADA (NF): {self.format_numeric_value_to_brl(totals['entrada'], decimals=2)}")
        self.totals_nfe_saida_label.config(text=f"TOTAIS DE SAÍDA (NF-e Mod. 55): {self.format_numeric_value_to_brl(totals['saida_nfe'], decimals=2)}")
        self.totals_reg61_label.config(text=f"TOTAIS DE SAÍDA (Consumidor Mod. 02): {self.format_numeric_value_to_brl(totals['saida_reg61'], decimals=2)}")
        self.totals_outras_saidas_label.config(text=f"TOTAIS DE OUTRAS SAÍDAS (NF): {self.format_numeric_value_to_brl(totals['outras_saidas'], decimals=2)}")

        for cfop, data in sorted(cfop_totals.items()):
            self.cfop_detailed_tree.insert("", tk.END, values=(cfop, self.format_numeric_value_to_brl(data['entrada'], decimals=2, include_rs=False), self.format_numeric_value_to_brl(data['saida'], decimals=2, include_rs=False)))
        
        for cst, data in sorted(cst_totals.items()):
            self.cst_totals_tree.insert("", tk.END, values=(cst, self.format_numeric_value_to_brl(data['valor_item'], decimals=2, include_rs=False), self.format_numeric_value_to_brl(data['base_icms'], decimals=2, include_rs=False)))

        for aliq, data in sorted(aliq_totals.items()):
            aliq_str = f"{aliq / 100.0:.2f}%".replace('.', ',')
            self.aliq_totals_tree.insert("", tk.END, values=(aliq_str, self.format_numeric_value_to_brl(data['base_icms'], decimals=2, include_rs=False), self.format_numeric_value_to_brl(data['valor_icms'], decimals=2, include_rs=False)))

        if "10" in self.sintegra_parsed_data and self.sintegra_parsed_data["10"]:
            p = self.parse_line_into_fields("10", self.sintegra_raw_lines[0], for_display=False)
            self.info_cnpj_label.config(text=f"CNPJ do Informante: {p.get('CNPJ', '').strip()}")
            self.info_ie_label.config(text=f"Inscrição Estadual: {p.get('Inscrição Estadual', '').strip()}")
            di = p.get('Data Inicial', ''); df = p.get('Data Final', '')
            self.info_periodo_label.config(text=f"Período: {di[0:2]}/{di[2:4]}/{di[4:8]} a {df[0:2]}/{df[2:4]}/{df[4:8]}")
        
        self.info_total_linhas_label.config(text=f"Total de Linhas no Arquivo: {len(self.sintegra_raw_lines)}")
        self.validate_trailer_and_fill_reg_counts()

    def validate_trailer_and_fill_reg_counts(self):
        # Implementação de validate_trailer_and_fill_reg_counts (sem alterações)
        trailer_counts = {}
        total_geral_trailer = "N/A"
        if "90" in self.sintegra_parsed_data:
            trailer_line = self.sintegra_raw_lines[self.sintegra_parsed_data["90"][-1]["line_index"]]
            pos = 30
            while pos < 118:
                r_type, count_str = trailer_line[pos:pos+2].strip(), trailer_line[pos+2:pos+10]
                if r_type and count_str.isdigit(): trailer_counts[r_type] = int(count_str)
                pos += 10
            if trailer_line[118:126].strip().isdigit(): total_geral_trailer = int(trailer_line[118:126].strip())

        all_record_types = sorted(list(set(self.sintegra_parsed_data.keys()) | set(trailer_counts.keys())))
        for r_type in all_record_types:
            if r_type == '90': continue
            real, declared = len(self.sintegra_parsed_data.get(r_type, [])), trailer_counts.get(r_type, "N/A")
            status = "OK" if real == declared else "DIVERGÊNCIA" if declared != "N/A" else "NÃO DECLARADO"
            self.reg_count_tree.insert("", tk.END, values=(r_type, self.record_descriptions.get(r_type, ""), real, declared, status), tags=(status,))
        
        total_real = len(self.sintegra_raw_lines)
        status_geral = "OK" if total_real == total_geral_trailer else "DIVERGÊNCIA" if total_geral_trailer != "N/A" else "SEM VALIDAÇÃO"
        self.reg_count_tree.insert("", tk.END, values=("TOTAL GERAL", "Todas as linhas do arquivo", total_real, total_geral_trailer, status_geral), tags=(status_geral,))
        self.reg_count_tree.tag_configure("DIVERGÊNCIA", background="#FFDDDD"); self.reg_count_tree.tag_configure("OK", background="#DDFFAA")


    def apply_styles(self):
        style = ttk.Style(); style.theme_use('clam')
        style.configure('TFrame', background='#EFEFEF'); style.configure('TLabel', background='#EFEFEF', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'), padding=5); style.configure('Treeview.Heading', font=('Arial', 10, 'bold'), background='#007ACC', foreground='#FFFFFF')
        style.map('Treeview.Heading', background=[('active', '#005F99')])
        style.configure('Treeview', font=('Consolas', 9), rowheight=22, background='#FFFFFF', fieldbackground='#FFFFFF')
        style.configure('TLabelframe.Label', font=('Arial', 11, 'bold'), background='#EFEFEF')
        self.data_tree.tag_configure('oddrow', background='#F8F8F8'); self.data_tree.tag_configure('evenrow', background='#E8E8E8')

    def load_sintegra_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")])
        if not file_path: return
        self.current_file_path = file_path
        self.file_label.config(text=os.path.basename(file_path))
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                self.sintegra_raw_lines = [line.rstrip('\r\n').ljust(126)[:126] for line in f if line.strip()]
            self.sintegra_parsed_data = defaultdict(list)
            for i, line in enumerate(self.sintegra_raw_lines):
                self.sintegra_parsed_data[line[:2]].append({"line_index": i})
            self.populate_record_type_listbox()
            self.notebook.select(self.edit_tab)
            messagebox.showinfo("Sucesso", "Arquivo SINTEGRA carregado!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao ler o arquivo: {e}")

    def parse_line_into_fields(self, record_type, line_content, for_display=True):
        fields_def = self.get_record_fields_info(record_type)
        parsed_fields = {}
        if not fields_def: return {"Linha Completa": line_content}
        
        for field in fields_def:
            val = line_content[field["start"]-1:field["end"]]
            if for_display:
                if field.get("decimals") is not None:
                    parsed_fields[field["name"]] = self.format_numeric_value_to_brl(val, decimals=field["decimals"])
                else:
                    parsed_fields[field["name"]] = val.strip()
            else:
                parsed_fields[field["name"]] = val
        return parsed_fields

    def populate_record_type_listbox(self):
        self.record_type_listbox.delete(0, tk.END)
        for r_type in sorted(self.sintegra_parsed_data.keys()):
            self.record_type_listbox.insert(tk.END, f"{r_type} ({len(self.sintegra_parsed_data[r_type])} regs)")

    def display_selected_record_type_data(self, event):
        selected_indices = self.record_type_listbox.curselection()
        if not selected_indices: return
        
        selected_item = self.record_type_listbox.get(selected_indices[0])
        self.current_selected_record_type = selected_item.split(" ")[0]
        
        self.current_record_type_label.config(text=f"REGISTRO {self.current_selected_record_type} - Detalhes")
        self.record_description_label.config(text=self.record_descriptions.get(self.current_selected_record_type, ""))
        
        self.clear_data_tree()
        fields_def = self.get_record_fields_info(self.current_selected_record_type)
        if not fields_def: return

        has_nf_col = any(f["name"] in ["Número", "Número NF", "Número inicial"] for f in fields_def)
        self.toggle_search_fields(has_nf_col)
        self.search_entry.delete(0, tk.END)

        self.data_tree["columns"] = [f["name"] for f in fields_def]
        for f in fields_def:
            self.data_tree.heading(f["name"], text=f["name"])
            self.data_tree.column(f["name"], width=max(len(f["name"]) * 8, f["size"] * 7, 70) + 15, anchor=tk.W)

        for i, line_data in enumerate(self.sintegra_parsed_data.get(self.current_selected_record_type, [])):
            line = self.sintegra_raw_lines[line_data["line_index"]]
            values = list(self.parse_line_into_fields(self.current_selected_record_type, line).values())
            self.data_tree.insert("", tk.END, iid=line_data["line_index"], values=values, tags=('oddrow' if i % 2 else 'evenrow',))

    def get_record_fields_info(self, record_type):
        # Definições completas e corrigidas
        fields_info = {
            "10": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Inscrição Estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Nome do Contribuinte", "size": 35, "start": 31, "end": 65, "format": "X"}, {"name": "Município", "size": 30, "start": 66, "end": 95, "format": "X"}, {"name": "UF", "size": 2, "start": 96, "end": 97, "format": "X"}, {"name": "Fax", "size": 10, "start": 98, "end": 107, "format": "N"}, {"name": "Data Inicial", "size": 8, "start": 108, "end": 115, "format": "N"}, {"name": "Data Final", "size": 8, "start": 116, "end": 123, "format": "N"}, {"name": "Cod. Estrutura", "size": 1, "start": 124, "end": 124, "format": "X"}, {"name": "Cod. Operações", "size": 1, "start": 125, "end": 125, "format": "X"}, {"name": "Cod. Finalidade", "size": 1, "start": 126, "end": 126, "format": "X"} ],
            "11": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "Logradouro", "size": 34, "start": 3, "end": 36, "format": "X"}, {"name": "Número", "size": 5, "start": 37, "end": 41, "format": "N"}, {"name": "Complemento", "size": 22, "start": 42, "end": 63, "format": "X"}, {"name": "Bairro", "size": 15, "start": 64, "end": 78, "format": "X"}, {"name": "CEP", "size": 8, "start": 79, "end": 86, "format": "N"}, {"name": "Nome Contato", "size": 28, "start": 87, "end": 114, "format": "X"}, {"name": "Telefone", "size": 12, "start": 115, "end": 126, "format": "N"} ],
            "50": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ/CPF", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Insc. Estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Data Emissão/Rec.", "size": 8, "start": 31, "end": 38, "format": "N"}, {"name": "UF", "size": 2, "start": 39, "end": 40, "format": "X"}, {"name": "Modelo", "size": 2, "start": 41, "end": 42, "format": "N"}, {"name": "Série", "size": 3, "start": 43, "end": 45, "format": "X"}, {"name": "Número", "size": 6, "start": 46, "end": 51, "format": "N"}, {"name": "CFOP", "size": 4, "start": 52, "end": 55, "format": "N"}, {"name": "Emitente", "size": 1, "start": 56, "end": 56, "format": "X"}, {"name": "Valor Total NF", "size": 13, "start": 57, "end": 69, "format": "N", "decimals": 2}, {"name": "Base Cálc. ICMS", "size": 13, "start": 70, "end": 82, "format": "N", "decimals": 2}, {"name": "Valor ICMS", "size": 13, "start": 83, "end": 95, "format": "N", "decimals": 2}, {"name": "Isenta/Não Trib.", "size": 13, "start": 96, "end": 108, "format": "N", "decimals": 2}, {"name": "Outras", "size": 13, "start": 109, "end": 121, "format": "N", "decimals": 2}, {"name": "Alíquota", "size": 4, "start": 122, "end": 125, "format": "N", "decimals": 2}, {"name": "Situação", "size": 1, "start": 126, "end": 126, "format": "X"} ],
            "51": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ/CPF", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Insc. Estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Data Emissão/Rec.", "size": 8, "start": 31, "end": 38, "format": "N"}, {"name": "UF", "size": 2, "start": 39, "end": 40, "format": "X"}, {"name": "Modelo", "size": 2, "start": 41, "end": 42, "format": "N"}, {"name": "Série", "size": 3, "start": 43, "end": 45, "format": "X"}, {"name": "Número", "size": 6, "start": 46, "end": 51, "format": "N"}, {"name": "CFOP", "size": 4, "start": 52, "end": 55, "format": "N"}, {"name": "Valor IPI", "size": 13, "start": 56, "end": 68, "format": "N", "decimals": 2}, {"name": "Valor Frete", "size": 13, "start": 69, "end": 81, "format": "N", "decimals": 2}, {"name": "Brancos", "size": 45, "start": 82, "end": 126, "format": "X"} ],
            "53": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Inscrição estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Data de emissão/recebimento", "size": 8, "start": 31, "end": 38, "format": "N"}, {"name": "Unidade da Federação", "size": 2, "start": 39, "end": 40, "format": "X"}, {"name": "Modelo", "size": 2, "start": 41, "end": 42, "format": "N"}, {"name": "Série", "size": 3, "start": 43, "end": 45, "format": "X"}, {"name": "Número", "size": 6, "start": 46, "end": 51, "format": "N"}, {"name": "CFOP", "size": 4, "start": 52, "end": 55, "format": "N"}, {"name": "Emitente", "size": 1, "start": 56, "end": 56, "format": "X"}, {"name": "Base de cálculo ICMS ST", "size": 13, "start": 57, "end": 69, "format": "N", "decimals": 2}, {"name": "ICMS retido", "size": 13, "start": 70, "end": 82, "format": "N", "decimals": 2}, {"name": "Despesas acessórias", "size": 13, "start": 83, "end": 95, "format": "N", "decimals": 2}, {"name": "Situação", "size": 1, "start": 96, "end": 96, "format": "X"}, {"name": "Código da antecipação", "size": 1, "start": 97, "end": 97, "format": "X"}, {"name": "Brancos", "size": 29, "start": 98, "end": 126, "format": "X"} ],
            "54": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Modelo", "size": 2, "start": 17, "end": 18, "format": "N"}, {"name": "Série", "size": 3, "start": 19, "end": 21, "format": "X"}, {"name": "Número NF", "size": 6, "start": 22, "end": 27, "format": "N"}, {"name": "CFOP", "size": 4, "start": 28, "end": 31, "format": "N"}, {"name": "CST", "size": 3, "start": 32, "end": 34, "format": "X"}, {"name": "Nº Item", "size": 3, "start": 35, "end": 37, "format": "N"}, {"name": "Cód. Produto", "size": 14, "start": 38, "end": 51, "format": "X"}, {"name": "Quantidade", "size": 11, "start": 52, "end": 62, "format": "N", "decimals": 3}, {"name": "Valor Item", "size": 12, "start": 63, "end": 74, "format": "N", "decimals": 2}, {"name": "Valor Desconto", "size": 12, "start": 75, "end": 86, "format": "N", "decimals": 2}, {"name": "Base ICMS", "size": 12, "start": 87, "end": 98, "format": "N", "decimals": 2}, {"name": "Base ICMS ST", "size": 12, "start": 99, "end": 110, "format": "N", "decimals": 2}, {"name": "Valor IPI", "size": 12, "start": 111, "end": 122, "format": "N", "decimals": 2}, {"name": "Alíquota ICMS", "size": 4, "start": 123, "end": 126, "format": "N", "decimals": 2} ],
            "61": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "Brancos_1", "size": 14, "start": 3, "end": 16, "format": "X"}, {"name": "Brancos_2", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Data de Emissão", "size": 8, "start": 31, "end": 38, "format": "N"}, {"name": "Modelo", "size": 2, "start": 39, "end": 40, "format": "N"}, {"name": "Série", "size": 3, "start": 41, "end": 43, "format": "X"}, {"name": "Subsérie", "size": 2, "start": 44, "end": 45, "format": "X"}, {"name": "Número inicial", "size": 6, "start": 46, "end": 51, "format": "N"}, {"name": "Número final", "size": 6, "start": 52, "end": 57, "format": "N"}, {"name": "Valor total", "size": 13, "start": 58, "end": 70, "format": "N", "decimals": 2}, {"name": "Base de cálculo ICMS", "size": 13, "start": 71, "end": 83, "format": "N", "decimals": 2}, {"name": "Valor do ICMS", "size": 12, "start": 84, "end": 95, "format": "N", "decimals": 2}, {"name": "Isenta ou não tributadas", "size": 13, "start": 96, "end": 108, "format": "N", "decimals": 2}, {"name": "Outras", "size": 13, "start": 109, "end": 121, "format": "N", "decimals": 2}, {"name": "Alíquota", "size": 4, "start": 122, "end": 125, "format": "N", "decimals": 2}, {"name": "Branco_Final", "size": 1, "start": 126, "end": 126, "format": "X"} ],
            "65": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ/CPF", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Insc. Estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Data Emissão", "size": 8, "start": 31, "end": 38, "format": "N"}, {"name": "Modelo", "size": 2, "start": 39, "end": 40, "format": "N"}, {"name": "Série", "size": 3, "start": 41, "end": 43, "format": "X"}, {"name": "Número", "size": 6, "start": 44, "end": 49, "format": "N"}, {"name": "CFOP", "size": 4, "start": 50, "end": 53, "format": "N"}, {"name": "Valor Total", "size": 13, "start": 54, "end": 66, "format": "N", "decimals": 2}, {"name": "Base Cálc. ICMS", "size": 13, "start": 67, "end": 79, "format": "N", "decimals": 2}, {"name": "Valor ICMS", "size": 13, "start": 80, "end": 92, "format": "N", "decimals": 2}, {"name": "Alíquota", "size": 4, "start": 93, "end": 96, "format": "N", "decimals": 2}, {"name": "Situação", "size": 1, "start": 97, "end": 97, "format": "X"}, {"name": "Brancos", "size": 29, "start": 98, "end": 126, "format": "X"} ],
            "74": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Modelo", "size": 2, "start": 17, "end": 18, "format": "N"}, {"name": "Série", "size": 3, "start": 19, "end": 21, "format": "X"}, {"name": "Nº Item", "size": 3, "start": 22, "end": 24, "format": "N"}, {"name": "Cód. Produto", "size": 14, "start": 25, "end": 38, "format": "X"}, {"name": "Quantidade", "size": 11, "start": 39, "end": 49, "format": "N", "decimals": 3}, {"name": "Valor", "size": 12, "start": 50, "end": 61, "format": "N", "decimals": 2}, {"name": "Data Inventário", "size": 8, "start": 62, "end": 69, "format": "N"}, {"name": "Motivo", "size": 1, "start": 70, "end": 70, "format": "X"}, {"name": "Brancos", "size": 56, "start": 71, "end": 126, "format": "X"}],
            "75": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "Data Inicial", "size": 8, "start": 3, "end": 10, "format": "N"}, {"name": "Data Final", "size": 8, "start": 11, "end": 18, "format": "N"}, {"name": "Cód. Produto", "size": 14, "start": 19, "end": 32, "format": "X"}, {"name": "Cód. NCM", "size": 8, "start": 33, "end": 40, "format": "N"}, {"name": "Descrição", "size": 53, "start": 41, "end": 93, "format": "X"}, {"name": "Unidade Medida", "size": 6, "start": 94, "end": 99, "format": "X"}, {"name": "Alíquota IPI", "size": 4, "start": 100, "end": 103, "format": "N", "decimals": 2}, {"name": "Alíquota ICMS", "size": 4, "start": 104, "end": 107, "format": "N", "decimals": 2}, {"name": "Red. Base ICMS", "size": 5, "start": 108, "end": 112, "format": "N", "decimals": 2}, {"name": "Base ICMS ST", "size": 5, "start": 113, "end": 117, "format": "N", "decimals": 2}, {"name": "Branco", "size": 9, "start": 118, "end": 126, "format": "X"} ],
            "90": [ {"name": "Tipo", "size": 2, "start": 1, "end": 2, "format": "N"}, {"name": "CNPJ", "size": 14, "start": 3, "end": 16, "format": "N"}, {"name": "Inscrição Estadual", "size": 14, "start": 17, "end": 30, "format": "X"}, {"name": "Registros", "size": 88, "start": 31, "end": 118, "format": "X"}, {"name": "Total Linhas Arquivo", "size": 8, "start": 119, "end": 126, "format": "N"} ]
        }
        return fields_info.get(record_type)

    def clear_data_tree(self):
        self.data_tree.delete(*self.data_tree.get_children()); self.data_tree["columns"] = []

    def on_cell_double_click(self, event):
        if not self.data_tree.selection(): return
        item_id = self.data_tree.selection()[0]
        col_id = self.data_tree.identify_column(event.x)
        column_index = int(col_id.replace('#', '')) - 1
        
        fields_def = self.get_record_fields_info(self.current_selected_record_type)
        if not fields_def or column_index >= len(fields_def): return
        
        field_info = fields_def[column_index]
        line_content = self.sintegra_raw_lines[int(item_id)]
        raw_val = line_content[field_info["start"]-1:field_info["end"]]
        
        decimals = field_info.get("decimals")
        display_val = self.format_numeric_value_to_brl(raw_val, decimals=decimals) if decimals is not None else raw_val.strip()

        editor = FieldEditorDialog(self, self.root, field_info["name"], display_val, field_info, is_monetary=bool(decimals))
        self.root.wait_window(editor.top)

        if editor.new_value_for_raw_line is not None:
            self.update_raw_sintegra_line_content(int(item_id), field_info, editor.new_value_for_raw_line)
            self.display_selected_record_type_data(None)

    def update_raw_sintegra_line_content(self, line_index, field_info, formatted_new_value):
        original_line = self.sintegra_raw_lines[line_index]
        start, end = field_info["start"] - 1, field_info["end"]
        new_line = original_line[:start] + formatted_new_value + original_line[end:]
        self.sintegra_raw_lines[line_index] = new_line.ljust(126)[:126]

    def format_numeric_value_to_brl(self, raw_value, decimals=2, include_rs=True):
        try:
            clean_val = int(''.join(filter(str.isdigit, str(raw_value))))
            divisor = 10.0 ** decimals
            float_val = clean_val / divisor
            formatted = f"{float_val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {formatted}" if include_rs else formatted
        except (ValueError, TypeError):
            return "R$ 0,00" if include_rs else "0,00"

    def save_sintegra_file(self):
        if not self.current_file_path: return messagebox.showwarning("Aviso", "Nenhum arquivo para salvar.")
        save_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=os.path.basename(self.current_file_path).replace(".txt", "_EDITADO.txt"))
        if not save_path: return
        try:
            with open(save_path, 'w', encoding='latin-1', newline='\r\n') as f:
                f.write("\n".join(self.sintegra_raw_lines) + "\n")
            messagebox.showinfo("Sucesso", f"Arquivo salvo com sucesso em: {save_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar o arquivo: {e}")

class FieldEditorDialog:
    def __init__(self, app, parent, field_name, current_val, field_info, is_monetary=False):
        self.app = app
        self.new_value_for_raw_line = None
        self.field_info = field_info
        self.is_monetary = is_monetary
        
        self.top = tk.Toplevel(parent); self.top.title(f"Editar: {field_name}"); self.top.geometry("450x200"); self.top.transient(parent); self.top.grab_set()
        ttk.Label(self.top, text=f"Campo: {field_name}", font=('Arial', 11, 'bold')).pack(pady=5)
        ttk.Label(self.top, text=f"Tam: {field_info['size']} | Pos: {field_info['start']}-{field_info['end']} | Formato: {'Numérico' if field_info['format'] == 'N' else 'Alfanumérico'}").pack()
        if is_monetary: ttk.Label(self.top, text=f"Use vírgula para {field_info.get('decimals', 2)} casas decimais", foreground='blue').pack()
        
        self.entry = ttk.Entry(self.top, width=50, font=('Consolas', 10)); self.entry.pack(pady=10, padx=10)
        self.entry.insert(0, str(current_val))
        self.entry.focus_set()
        
        btn_frame = ttk.Frame(self.top); btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Salvar", command=self.save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Cancelar", command=self.top.destroy).pack(side=tk.RIGHT, padx=10)
        self.top.bind('<Return>', lambda e: self.save()); self.top.bind('<Escape>', lambda e: self.top.destroy())

    def save(self):
        val = self.entry.get()
        size = self.field_info['size']
        try:
            if self.is_monetary:
                decimals = self.field_info.get('decimals', 2)
                multiplier = 10 ** decimals
                float_val = float(val.replace("R$", "").strip().replace(".", "").replace(",", "."))
                int_val = int(round(float_val * multiplier))
                raw_val = str(abs(int_val)).rjust(size, '0')
            elif self.field_info['format'] == 'N':
                if not val.isdigit(): raise ValueError("Apenas dígitos são permitidos.")
                raw_val = val.rjust(size, '0')
            else: # Alfanumérico
                raw_val = val.ljust(size, ' ')
            
            if len(raw_val) > size:
                raise ValueError(f"Valor excede o tamanho máximo de {size} caracteres.")

            self.new_value_for_raw_line = raw_val[:size]
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Erro de Validação", str(e), parent=self.top)

if __name__ == "__main__":
    root = tk.Tk()
    app = SintegraEditorApp(root)
    root.mainloop()