import sqlite3 as lite
class Loader():
	def __init__(self):
		self.worksheets = {}
		self.cell_ranges = {}
		self.indexed = False
		self.cellIndexed = False
		self.db_name = 'database/db.db'
		self.tables_names = []
		self.is_open = False
		for item in self.get_tables_names():
			if 'exp' in item.split('_'):
				self.tables_names.append(item)
		
	# creates sql connection with the database.
	def setup(self):
		if not self.is_open:
		    # ignore threading check
			# Dangerous? probably.
			self.conn = lite.connect(self.db_name, check_same_thread=False)
			self.is_open = True

	# close sql connection.
	def tear_down(self):
		if self.conn:
			self.conn.close()
			self.is_open = False
	
	# autocomplete from sqlite database
	def get_auto_complete_names(self, gene_symbol):
		self.setup()
		# change after database update.
		query = ''.join(["SELECT gene_name from Female_Male_exp_levels_log2 WHERE gene_name LIKE '%",gene_symbol,"%'"," LIMIT 50"])
		cursor = self.conn.execute(query)
		names = list(set(list(map(lambda x:x[0], cursor.fetchall()))))
		return names		
		

	# input: table name.
	# returns a list of columns names in a table.
	def get_columns_names(self,table_name):
		query = ' '.join(['SELECT * from',table_name])
		cursor = self.conn.execute(query)
		names = list(map(lambda x:x[0], cursor.description))
		return names

	# returns a list of names of the tables in the database
	def get_tables_names(self):
		self.setup()
		cursor = self.conn.cursor()
		cursor.execute('SELECT name FROM sqlite_master WHERE type="table";')
		tables_names = list(map(lambda x:x[0],cursor.fetchall()))
		self.tear_down()
		return tables_names

	# input:
	# condition: condition of the query, defaults to gene_name.
	# value: the value of the condition.
	# dataset: the table name.
	# cells: a cell type, if the value is ALL, will select all columns. default to ALL
	# output:
	# A query command according to input.
	def get_select_command(self,value,dataset,cells='ALL',condition='gene_name'):
		if cells == 'ALL':
			cells = '*'	
		else:
			cells = ', '.join(self.get_cells_names(cells,dataset))
		command = ' '.join(['SELECT',cells,'from',dataset,'where',condition,'=',''.join(['"',value,'"'])])
		return command

	# the function takes a gene_name, a list of datasets dirs, which can be set to 'ALL'
	# and an optional argument of cell type for cell specific graphs
	# returns a dictionary where the keys are the datasets and the values are lists of expression data 
	# for each row of the wgene in the database. 	
	def get_gene(self,gene_name,datasets='ALL',cells='ALL'):
		self.setup()
		data = {}
		noise_data = {}
		if datasets == 'ALL':
			datasets = self.tables_names
		for dataset in datasets:
			values_list = self.get_gene_data(gene_name,dataset,cells)
			if cells == 'ALL':
				colms = self.get_columns_names(dataset)
			else:
				colms = self.get_cells_names(cells,dataset)
			data_tuples = {}
			for index,values in enumerate(values_list):
				key = '_'.join(['repeat',str(index+1)])
				data_tuples[key] = zip(colms,values)
			data[dataset] = data_tuples
			noise_data[dataset] = self.get_noise(gene_name,dataset)
		self.tear_down()
		return data, noise_data

    # get noise values
	def get_noise(self, gene_name, dataset):
		query = ''.join(['SELECT noise from ', dataset,' where gene_name = "', gene_name, '"'])
		cursor = self.conn.execute(query)
		data = []
		for row in cursor:
			data.append(list(row))
		return data

	# input:
	# cell_type: the type of cell, for example: 'GN','B1a'
	# table: the table name in the sql shema. get it from get_tables_names
	# returns a list of cells of the same type of the input cell.
	def get_cells_names(self,cell_type,table):
		cells = self.get_columns_names(table)
		cells_types = [cell_type]
		cells_names = []
		if cell_type.upper() == 'B1AB':
			cells_types.append('B1A')
		elif cell_type.upper() == 'CD19':
			cells_types.append('B')
		elif cell_type.upper() == 'T8':
			cells_types.append('CD8T')
		elif cell_type.upper() == 'T4':
			cells_types.append('CD4T')
		
		for cell in cells:
			for item in cells_types:
				if item.upper() in cell.upper().split('_'):
					cells_names.append(cell)
		return cells_names

	# input:
	# gene_name is the gene symbol
	# data_set is the table name in the sql database (the dataset)
	# cells is a list of cells to get values for (columns in the sql dataset). defaults to ALL.
	def get_gene_data(self,gene_name,data_set,cells='ALL'):	
		cursor = self.conn.execute(self.get_select_command(gene_name,data_set,cells))
		data = []
		for row in cursor:
			data.append(list(row))
		return data
 		

