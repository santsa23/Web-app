from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from elasticsearch import Elasticsearch
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)
es = Elasticsearch(hosts=['http://localhost:9200'])  # Verbindung zu Elasticsearch herstellen

class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    category = StringField('Category')
    submit = SubmitField('Submit')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ProductForm()
    if form.validate_on_submit():
        new_product = Product(
            name=form.name.data,
            description=form.description.data,
            category=form.category.data
        )
        db.session.add(new_product)
        db.session.commit()

        # Indexiere das Produkt in Elasticsearch
        es.index(index='products', doc_type='_doc', body={
            'name': new_product.name,
            'description': new_product.description,
            'category': new_product.category
        })

        flash('Product added successfully!', 'success')
        return redirect(url_for('index'))

    products = Product.query.all()
    return render_template('index.html', form=form, products=products)

@app.route('/search')
def search():
    query = request.args.get('query', '')
    print(f"Received query: {query}")

    # Führe die Elasticsearch-Suche durch
    search_results = es.search(index='products', body={
        'query': {
            'match': {
                'name': query
            }
        }
    })
    print(f"Elasticsearch results: {search_results}")

    # Extrahiere die relevanten Informationen aus den Suchergebnissen
    hits = search_results.get('hits', {}).get('hits', [])
    products = [{'name': hit['_source']['name'], 'description': hit['_source']['description']} for hit in hits]

    return render_template('index.html', query=query, products=products)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # Hier kannst du Elasticsearch-Abfragen ausführen oder andere erforderliche Elasticsearch-Aktionen durchführen

    app.run(debug=True)