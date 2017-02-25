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
    cells = get_colimn_names(dataset)
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

@app.route('/hello',methods=['GET','POST'])
def hello():
    def say_hi(obj_response):
        obj_response.alert('Hi there!')

    if flask.g.sijax.is_sijax_request:
        #print "REQUEST"
        flask.g.sijax.register_callback('say_hi', say_hi)
        return flask.g.sijax.process_request()

    return flask.render_template('test.html')


@app.route('/genes/cell_type_specific/<gene_name>/<cell_type>')
def ctc_gene(gene_name, cell_type):
    form = forms.CellTypeSpecificForm()
    return flask.render_template('cell_type_specific.html',form=form)


@app.route('/genes/pan_immune/<gene_name>')
def pi_gene(gene_name):
    search_form = forms.GeneSearchForm()
    
    gene_data, noise_data = get_pi_gene(gene_name)

    head_cols = ['ID','gene_name', 'chr','start','end']
    # create graphs for every repeat
    for dataset in gene_data:
        for gene_repeat in gene_data[dataset]:
            all_columns = list(gene_data[dataset][gene_repeat])
            # general information about the gene: chr, name, id, start, end.
            header = dict(all_columns[:5]) 
            cells_column = dict(all_columns[5:])
            # create male data
            male_data = []
            IFN_male_data = []
            female_data = []
            IFN_female_data = []
            noise_level = 0
            index = 0
            last_cell_name = ''
            cells_axis = []
            for cell in cells_column:
                parts = cell.split('_')
                if (parts[0] != last_cell_name):
                    index +=1 
                    cells_axis.append((parts[0],index))
                last_cell_name = parts[0]
                exp_level = round(float(cells_column[cell]),3)
                if 'M' in parts or 'male' in parts:
                    # male cell
                    if '10kIFN' in parts or '1kIFN' in parts:
                        # IFN cell
                        IFN_male_data.append((exp_level,index)) 
                    else:
                        male_data.append((exp_level,index))
                elif 'F' in parts or 'female' in parts:
                    # female cell
                    if '10kIFN' in parts or '1kIFN' in parts:
                        # IFN cell
                        IFN_female_data.append((exp_level,index))
                    else:
                        female_data.append((exp_level,index))
                elif 'noise' in parts:
                    noise_level = exp_level
                # create graph for the data
            # remove the noise from the cells axis
            cells_axis.pop(-1)
            print(cells_axis)
            # remember to change B1ab to B1a and CD19 to B in all cells_axis

    return flask.render_template('pan_immune.html',form=search_form)

@flask_sijax.route(app,'/test')
def test():
    def say_hi(obj_response):
        obj_response.alert('hi')

    if g.sijax.is_sijax_request:
        g.sijax.register_callback('say_hi',say_hi)
        return g.sijax.process_request()

    return render_template('test.html')


if __name__ == "__main__":
	app.run(debug=True,host='0.0.0.0')

