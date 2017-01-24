# libs
import flask
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
app.config['SIJAX_JSON_URI'] = sijax_path + 'json2.js'#'/static/js/sijax/json2.js'
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
        print "WOW"
        print options
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
    with open ('sedit/static/data/pi_uri_data', 'r') as f:
        pi_uri = f.read()
    with open ('sedit/static/data/ctc_uri_data', 'r') as f:
        ctc_uri = f.read()
    return flask.render_template('about.html',pi_graph = pi_uri, ctc_graph = ctc_uri)


@app.route('/genes/pan_immune',methods=['GET', 'POST'])
def pan_immune():
    search_form = forms.GeneSearchForm()
    if flask.request.method == 'POST':
        if flask.g.sijax.is_sijax_request:
      	    flask.g.sijax.register_callback('autocomplete',autocomplete)
            return flask.g.sijax.process_request()
        else:
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
        print "REQUEST"
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
    return flask.render_template('pan_immune.html',form=search_form)

if __name__ == "__main__":
	app.run(debug=True)

