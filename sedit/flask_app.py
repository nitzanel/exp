# libs
import flask
from flask import url_for, g, session, render_template
import os
import flask_sijax
from flask_wtf.csrf import CsrfProtect
import hmac
from hashlib import sha1
import pygal
# modules
import forms
import sqlite3

from styles import pi_style_3, pi_style_5, ctc_style_3, ctc_style_5

app = flask.Flask(__name__)
# config flask app
sijax_path = os.path.join('.', os.path.dirname(__file__), 'static/js/sijax/')
app = flask.Flask(__name__.split('.')[0])
app.secret_key = os.urandom(128)
app.config['SIJAX_STATIC_PATH'] = sijax_path
# not sure why next line works
#app.config['SIJAX_JSON_URI'] = '/static/js/sijax/json2.js'
# fixed error with sijax
flask_sijax.Sijax(app)

#
FILTER_VALUE = 5.0

# change when deploying
DATABASE = 'database/db.db'
# protection #
CsrfProtect(app)




""" DATABASE FUNCTIONS """
# get the db
def get_db():
    db = getattr(flask.g, '_database', None)
    if db is None:
        db = flask.g._database = sqlite3.connect(DATABASE,check_same_thread=False)
    return db

# close the db
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(flask.g, '_database', None)
    if db is not None:
        db.close()

# creates a html option tag, for the autocomplete.
# input: gene_symbol - an autocomplete string.
def create_tag(gene_symbol):
	tag = ''.join(["<option value='",gene_symbol,"'></option>"])
	return tag

# autocomplete helper
class ACHelper(object):
	def __init__(self):
		self.last_value = ''
		self.last_options = []
	def change_last(self,value,options):
		self.last_value = value
		self.last_options = options

ac_helper = ACHelper()

def get_autocomplete_names(self, gene_symbol):
    db = get_db()
	# change after database update.
    query = ''.join(["SELECT gene_name from Female_Male_exp_levels_log2 WHERE gene_name LIKE '%",gene_symbol,"%'"," LIMIT 50"])
    cursor = db.execute(query)
    names = list(set(list(map(lambda x:x[0], cursor.fetchall()))))
    return names

# not working
def autocomplete(obj_response, value):
    if len(value) < 1:
        return
    if '"' in value or "'" in value or '?' in value or '!' in value or '%' in value or '&' in value:
        return
    options = []
    if ac_helper.last_value == value:
        return
    else:
        options = get_autocomplete_names(value)
        options = list(map(create_tag, options))
        ac_helper.change_last(value,options) 
		# fill options according to value
        # create a list of tags
        # add autocomplete options, and clear the previous ones.
    obj_response.html('#genes_datalist','')
    obj_response.html_append('#genes_datalist',''.join(options))

@app.template_global('csrf_token')
def csrf_token():
    """
    Generate a token string from bytes arrays. The token in the session is user
    specific.
    """
    if "_csrf_token" not in flask.session:
        flask.session["_csrf_token"] = os.urandom(128)
    return hmac.new(app.secret_key, flask.session["_csrf_token"],
                    digestmod=sha1).hexdigest()


# db loading functions #
def get_datasets_names():
    db_conn = get_db()
    cursor = db_conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table";')
    datasets_names = list(map(lambda x:x[0], cursor.fetchall()))
    return datasets_names


def get_columns_names(table_name):
		query = ' '.join(['SELECT * from',table_name])
		cursor = get_db().execute(query)
		names = list(map(lambda x:x[0], cursor.description))
		return names


def get_cells_names(cell_type,dataset):
    cells = get_columns_names(dataset)
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
# creates a query
def get_select_command(value,dataset,cells='ALL',condition='gene_name'):
    if cells == 'ALL':
        cells = '*'
    else:
        cells = ', '.join(get_cells_names(cells,dataset))
    command = ' '.join(['SELECT',cells,'from',dataset,'where',condition,'=',''.join(['"',value,'"'])])
    return command


# do a query and get list of data
def get_gene_data(gene_name, dataset, cells='ALL'):
    cursor = get_db().execute(get_select_command(gene_name,dataset,cells))
    data = []
    for row in cursor:
        data.append(list(row))
    return data
    
def get_noise(gene_name,dataset):
    query = ''.join(['SELECT noise from ', dataset,' where gene_name = "', gene_name, '"'])
    cursor = get_db().execute(query)
    data = []
    for row in cursor:
        data.append(list(row))
    return data


def get_ctc_gene(gene_name,cell_type):
    data = {}
    noise_data = {}
    datasets = get_datasets_names()
    
    for dataset in datasets:
        values_list = get_gene_data(gene_name,dataset,cell_type)
        #print ('dataset:',dataset)
        colms = get_columns_names(dataset)
        data_tuples = {}
        for index, values in enumerate(values_list):
            key = '_'.join(['repeat',str(index+1)])
            data_tuples[key] = zip(colms,values)
        data[dataset] = data_tuples
    return data

def get_pi_gene(gene_name):
    data = {}
    noise_data = {}
    datasets = get_datasets_names() 
    
    for dataset in datasets:
        values_list = get_gene_data(gene_name,dataset,'ALL')
        colms = get_columns_names(dataset)
        data_tuples = {}
        for index, values in enumerate(values_list):
            key = '_'.join(['repeat',str(index+1)])
            data_tuples[key] = zip(colms,values)
        data[dataset] = data_tuples
        noise_data[dataset] = get_noise(gene_name, dataset)
    return (data, noise_data)

# some utility functions

#takes a list of tuples
def fix_names(names):
    fixed_names = []
    for tup in names:
        cell_name = tup[0]
        if cell_name == 'B1ab':
            cell_name = 'B1a'
        elif cell_name == 'CD19':
            cell_name = 'B'
        new_tup = (cell_name,tup[1])
        fixed_names.append(new_tup)

    return fixed_names

# takes a list of tuples
def create_x_labels(names):
    x_labels = []
    for pair in names:
        label = {}
        label['label'] = pair[0]
        label['value'] = pair[1]
        x_labels.append(label)
    return tuple(x_labels)

# get the dataset symbol
def get_ds_name(ds):
    if ds.startswith('FM_IFN'):
        return 'A'
    elif ds.startswith('ImmGen'):
        return  'B'
    elif ds.startswith('Female_Male'):
        return 'C'
    elif ds.startswith('pilot8'):
        return 'D'
    else:
        return 'unknown'

# get ordered graphs - order will be A-B-C-D-others
def order_graphs(graphs,extended = False):
    graph_A =[]
    graph_B =[]
    graph_C =[]
    graph_D =[]
    future_wierd = []
    ordered_graphs = []
    for graph in graphs:
        if 'A' in graph.title:
            graph_A.append(graph)
        elif 'B' in graph.title:
            graph_B.append(graph)
        elif 'C' in graph.title:
            graph_C.append(graph)
        elif 'D' in graph.title:
            graph_D.append(graph)
        else:
            future_wierd.append(graph)
    if extended:  
        ordered_graphs = graph_A + graph_B + graph_C + graph_D + future_wierd
    else:
        ordered_graphs.append(graph_A[0])
        ordered_graphs.append(graph_B[0])
        ordered_graphs.append(graph_C[0])
        ordered_graphs.append(graph_D[0])
   
    return ordered_graphs

# graphs creation
def create_pi_graphs(gene_name):
    gene_data, noise_data = get_pi_gene(gene_name)
    graphs = []
    header = []
    head_cols = ['ID','gene_name', 'chr','start','end']
    # create graphs for every repeat
    for dataset in gene_data:
        for gene_repeat in gene_data[dataset]:
            all_columns = list(gene_data[dataset][gene_repeat])
            # general information about the gene: chr, name, id, start, end.
            header = dict(all_columns[:5]) 
            cells_column = dict(all_columns[5:])
           
            male_data = []
            IFN_male_data = []
            female_data = []
            IFN_female_data = []
            noise_level = 0
            index = 0
            last_cell_name = ''
            cells_axis = []
            max_exp_value = 0.0
            for cell in cells_column:
                parts = cell.split('_')
                if (parts[0] != last_cell_name):
                    index +=1 
                    cells_axis.append((parts[0],index))
                last_cell_name = parts[0]
                exp_level = round(float(cells_column[cell]),3)
                if max_exp_value < exp_level:
                    max_exp_value = exp_level
                if 'M' in parts or 'male' in parts:
                    # male cell
                    if '10kIFN' in parts or '1kIFN' in parts:
                        # IFN cell
                        IFN_male_data.append((index+0.1,exp_level)) 
                    else:
                        male_data.append((index-0.1,exp_level))
                elif 'F' in parts or 'female' in parts:
                    # female cell
                    if '10kIFN' in parts or '1kIFN' in parts:
                        # IFN cell
                        IFN_female_data.append((index+0.1,exp_level))
                    else:
                        female_data.append((index-0.1,exp_level))
                elif 'noise' in parts:
                    noise_level = exp_level
                # create graph for the data
            # remove the noise from the cells axis
            cells_axis.pop(-1)
            cells_axis = fix_names(cells_axis)
            cells_axis = create_x_labels(cells_axis)
            style = pi_style_3
            if get_ds_name(dataset) == 'A':
                style = pi_style_5
            # remember to create pi_style
            graph = pygal.XY(stroke=False,
                            show_y_guides=False,
                            truncate_label=-1,
                            dots_size=4,
                            legend_at_bottom=True,
                            style=style
                            )
           
            # round the max expresison value
            max_exp_value = int(max_exp_value)
            if max_exp_value >= 5:
                graph.range = (0,max_exp_value +1)
            else:
                graph.range = (0, 5)
            
            graph.title = "{} in DataSet {}".format(gene_name,
                                                    get_ds_name(dataset))
            if noise_level < 1.0:
                graph.title += ' noise level low'
            graph.y_title = "Log2 (expression level)"
            filter_line = [(0.1 * x,FILTER_VALUE) for x in range(0,110,2)]
            graph.add('Female',female_data)
            graph.add('Males',male_data)
            
            if get_ds_name(dataset) == 'A':
                graph.add('IFN_female',IFN_female_data)
                graph.add('IFN_male', IFN_male_data)
            graph.x_labels = cells_axis
            graph.add('Noise threshold',filter_line, color='#333333')
            graphs.append(graph)
    
    return graphs, header


# create a ctc-graph
def create_ctc_graph(gene_name,cell_type, show_repeats=False):
    gene_data = get_ctc_gene(gene_name,cell_type)
    graphs = []
    header = []
    index = 0
    head_cols = ['ID','gene_name', 'chr','start','end']
    
    IFN_male =[]
    IFN_female=[]
    male=[]
    female=[]
    max_exp_value = 0.0
    # create graphs for every repeat
    for dataset in gene_data:
        if get_ds_name(dataset) == 'A':
            index =1
        elif get_ds_name(dataset) == 'B':
            index =2 
        elif get_ds_name(dataset) == 'C':
            index =3
        elif get_ds_name(dataset) == 'D':
            index =4
        else:
            index =5
        male_data = []
        IFN_male_data = []
        female_data = []
        IFN_female_data = []
      
        for gene_repeat in gene_data[dataset]:    
            cells_axis = []
            all_columns = list(gene_data[dataset][gene_repeat])
            for cell in all_columns:
                parts = cell[0].split('_')
                exp_level =round(float(cell[1]), 3)
                max_exp_value = max(exp_level,max_exp_value)
                if 'M' in parts or 'male' in parts:
                # male cell
                    if '10kIFN' in parts or '1kIFN' in parts:
                    # IFN cell
                        IFN_male_data.append((index+0.1,exp_level)) 
                    else:
                        male_data.append((index-0.1,exp_level))
                elif 'F' in parts or 'female' in parts:
                # female cell
                    if '10kIFN' in parts or '1kIFN' in parts:
                    # IFN cell
                        IFN_female_data.append((index+0.1,exp_level))
                    else:
                        female_data.append((index-0.1,exp_level))
     
            IFN_male += IFN_male_data
            IFN_female += IFN_female_data
            male += male_data
            female += female_data
    # all data prepared
    style = ctc_style_3
    if cell_type in ['GN','MF','B']:
        style = ctc_style_5
        
    graph = pygal.XY(stroke=False,
                    show_y_guides=False,
                    truncate_label=-1,
                    dots_size=4,
                    legend_at_bottom=True,
                    style=style
                    )
   
    graph.add('female',female)
    graph.add('male', male)
    if cell_type in ['GN','MF','B']:
        graph.add('IFN_female',IFN_female)
        graph.add('IFN_male',IFN_male)
    
    
    filter_line = [(0.1 * x,FILTER_VALUE) for x in range(0,40,2)]
    graph.add('Noise threshold', filter_line)

    x_labels = []
    x_labels.append({'value':1, 'label':'A'})        
    x_labels.append({'value':2, 'label':'B'})
    x_labels.append({'value':3, 'label':'C'})
    x_labels.append({'value':4, 'label':'D'})
    graph.x_labels = x_labels
    if max_exp_value >5:
        graph.range = (max_exp_value+1)
    else:
        graph.range = (0,5)
    graph.title = "{} in {} ".format(gene_name, cell_type)
    graph.y_title = "Log2 (expression level)"
    print ('created graph: {}'.format(graph)) 
    return graph
# routes #

@app.route('/')
def home():
    get_db()
    return flask.redirect(flask.url_for('pan_immune'))


@app.route('/genes')
def genes():
    return flask.redirect(flask.url_for('pan_immune'))


@app.route('/about')
def about():
	# get the pi and ctc graphs examples
    pi_uri = ''
    ctc_uri = ''
    with open ('static/data/pi_uri_data', 'r') as f:
        pi_uri = f.read()
    with open ('static/data/ctc_uri_data', 'r') as f:
        ctc_uri = f.read()
    return flask.render_template('about.html',pi_graph = pi_uri, ctc_graph = ctc_uri)


@app.route('/genes/pan_immune',methods=['GET', 'POST'])
def pan_immune():
    search_form = forms.GeneSearchForm()
    if flask.request.method == 'POST':
        print ("TEST")
        if flask.g.sijax.is_sijax_request:
            flask.g.sijax.register_callback('autocomplete',autocomplete)
            return flask.g.sijax.process_request()
        pi_gene_url = '/'.join(['genes','pan_immune',flask.request.form['gene_name'].upper()])
        return flask.redirect(pi_gene_url)
    return flask.render_template('pan_immune.html',form=search_form)


@app.route('/genes/cell_type_specific',methods=['GET', 'POST'])
def cell_type_specific():
    form = forms.CellTypeSpecificForm()
    if flask.request.method == 'POST':
        if flask.g.sijax.is_sijax_request:
            flask.g.sijax.register_callback('autocomplete',autocomplete)
            return flask.g.sijax.process_request()
        else:
            ctc_gene_url = '/'.join(['genes','cell_type_specific',flask.request.form['gene_name'].upper(),flask.request.form['cell_type'].upper()])
            return flask.redirect(ctc_gene_url)
    return flask.render_template('cell_type_specific.html',form=form)



@app.route('/genes/cell_type_specific/<gene_name>/<cell_type>')
def ctc_gene(gene_name, cell_type):
    form = forms.CellTypeSpecificForm()
    graph= create_ctc_graph(gene_name,cell_type) 
 
    return flask.render_template(
                                'cell_type_specific.html',
                                graph=graph,
                                form=form,
                                )


@app.route('/genes/pan_immune/<gene_name>')
def pi_gene(gene_name):
    search_form = forms.GeneSearchForm()
    
    graphs,header = create_pi_graphs(gene_name)
    header = "gene:{} chr:{}  start:{}  end:{}".format(
                                        header['gene_name'],
                                        header['chr'],
                                        header['start'],
                                        header['end']
                                        )
    # order the graphs and get one of each set
    graphs = order_graphs(graphs,False)
    graphs = list(map(lambda graph: graph.render_data_uri(),graphs))
    # dont forget the noise
    is_extended = False
    return flask.render_template(
                                'pan_immune.html',
                                form=search_form,
                                graphs=graphs, 
                                header = header, 
                                is_extended=is_extended,
                                gene_name=gene_name
                                )

@app.route('/genes/pan_immune/<gene_name>/ext')
def pi_gene_ext(gene_name):
    search_form = forms.GeneSearchForm()
    
    graphs,header = create_pi_graphs(gene_name)
    header = "gene:{} chr:{}  start:{}  end:{}".format(
                                        header['gene_name'],
                                        header['chr'],
                                        header['start'],
                                        header['end']
                                        )
    # order the graphs and get all of them
    graphs = order_graphs(graphs,True)
    graphs = list(map(lambda graph: graph.render_data_uri(),graphs))
    is_extended = True
    # dont forget the noise
    return flask.render_template(
                                'pan_immune.html',
                                form=search_form,
                                graphs=graphs,
                                header = header,
                                is_extended=is_extended,
                                gene_name=gene_name
                                )


if __name__ == "__main__":
	# when deployong dont forget to set debug to False
    app.run(debug=True,host='0.0.0.0')

