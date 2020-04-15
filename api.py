from flask import Flask
from flask_restx import Api, Resource, fields, cors
# from werkzeug.contrib.fixers import ProxyFix
from flask_cors import CORS, cross_origin
import numpy as np
from elastic_util import ElasticUtil, ElasticUtilNameId
from wikiscraper import WikiScraper
from graph import pre_create_graph, create_graph

app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': 'http://localhost:3000'}})

# app.wsgi_app = ProxyFix(app.wsgi_app)
api = Api(app, version='0.0', title='Contents Network API',
    description='A simple Conents Network API',
    doc='/doc/',
)

ns_users = api.namespace('users', description='users data')
ns_contents = api.namespace('contents', description='contents data')
ns_graphs = api.namespace('graph', description='contents graph')

user = api.model('User', {
    'id': fields.String(attribute='_id', readonly=True, description='The name of user'),
    'data': fields.Raw(attribute='_source', required=True, description='Dict of contents and score')
})
content = api.model('Content', {
    'name': fields.String(attribute='_source.name', description='The name of content'),
    'wiki_id': fields.Integer(required=False, default=-1, example=-1, description='The wikipedia page id'),
    'data': fields.Raw(attribute='_source', readonly=True, required=True, description='data')
})

# need to be restful?
graph = api.model('Graph', {
    'id': fields.String(readonly=True, description='The name of user'),
    'data': fields.Raw(required=True, description='Dict of contents and score'),
    'graph': fields.Raw(readonly=True, description='nodes and edges')
})

eu_user = ElasticUtil(index='users')
eu_content = ElasticUtilNameId(index='contents')

@ns_users.route('/')
class UserList(Resource):
    '''Shows a list of all user, and lets you POST to add new tasks'''
    @ns_users.doc('List Users')
    @ns_users.marshal_list_with(user)
    def get(self):
        '''List all Users'''
        return eu_user.get_all()

    @ns_users.doc('Create sers')
    @ns_users.expect(user)
    # @ns_users.marshal_with(user)
    def post(self):
        '''List all Users'''
        res = eu_user.post(api.payload['data'])
        return res

@ns_users.route('/<string:id>')
@ns_users.response(404, 'User not found')
class User(Resource):
    '''Show a single user'''
    @ns_users.doc('get_user')
    @ns_users.marshal_with(user)
    def get(self, id):
        '''Fetch a given User'''
        return eu_user.get(id)

    @ns_users.doc('Add/Update_user')
    @ns_users.expect(user)
    # @ns_users.marshal_with(user, code=201)
    def put(self, id):
        '''Add/Update user'''
        res = eu_user.put(id, api.payload['data'])
        return res



def wiki_id_check(wiki_id):
    return  np.nan if wiki_id <0 else wiki_id

def wiki_load(name, wiki_id):
    wsc = WikiScraper()
    res, wiki_data = wsc.load(name=name, pageid=wiki_id, lang='ja')
    if not res:
        msg = name + ' not found in wikipedia. Please try again'
        if api.payload['wiki_id']<0:
            msg += ' or try with page id.'
        else:
            msg += '.'
        return msg, 404
    return wiki_data, 200

@ns_contents.route('/')
class ContentList(Resource):
    '''Shows a list of all contents, and lets you POST to add new tasks'''
    @ns_contents.doc('List_Contents')
    @ns_contents.marshal_list_with(content)
    def get(self):
        '''List all tasks'''
        # return DAO.Contents
        return eu_content.get_all()

    @ns_contents.doc('create_todo')
    @ns_contents.expect(content)
    # @ns_contents.marshal_with(content, code=201)
    def post(self):
        '''Create a new task'''
        name = api.payload['name']

        #check exist
        res, code = eu_content.get(name)
        if code != 404:
            return name + ' is exist', 400

        #get data from wiki        
        res, code = wiki_load(name, wiki_id_check(api.payload['wiki_id']))
        if code==404:
            return res, code

        wiki_data = res
        #post data to the elastic search
        res, code = eu_content.post(name, wiki_data)
        if code==201:
            return wiki_data, code

        return res, code

@ns_contents.route('/<string:name>')
@ns_contents.response(404, 'Content not found')
class Content(Resource):
    '''Show a single todo item and lets you delete them'''
    @ns_contents.doc('get_contentes')
    @ns_contents.marshal_with(content)
    def get(self, name):
        '''Fetch a given resource'''
        return eu_content.get(name)

    @ns_contents.expect(content)
    # @ns_contents.marshal_with(content)
    def put(self, name):
        '''Update a task given its identifier'''

        #get data from wiki        
        res, code = wiki_load(name, wiki_id_check(api.payload['wiki_id']))
        if code==404:
            return res, code

        wiki_data = res
        #post data to the elastic search
        res, code = eu_content.put(name, wiki_data)
        if code==200:
            return wiki_data, code

        return res, code


@ns_graphs.route('/get_from_id/<string:id>')
class GraphFromId(Resource):
    '''Show a single user'''
    @ns_graphs.doc('get_graph')
    @ns_graphs.marshal_with(graph)
    # @ns_graphs.expect(graph)
    def get(self, id):
        '''Fetch a given User'''

        #get data from userid
        res, code = eu_user.get(id)
        if code!=200:
            return res, code

        input_data = res['_source']
        points = {}
        data = {}
        for name in input_data.keys() :
            if 'checked' in input_data[name].keys() and 'checked':
                points[name] = float(input_data[name])
                res, code = eu_content.get(name)
                if code==200:
                    data[name] = res['_source']
                else:
                    print(res, code)

        G = create_graph(pre_create_graph(points=points, data=data)) 
        res = {'id': id, 'data':input_data, 'graph':{}}
        res['graph']['nodes'] = dict(G.nodes)
        res['graph']['edges'] = G.edges.__str__()

        return res, 200

@ns_graphs.route('/get_from_data')
class GraphFromData(Resource):
    '''Show a single user'''
    @ns_graphs.doc('get_graph')
    @ns_graphs.marshal_with(graph)
    @ns_graphs.expect(graph)
    def post(self):
        '''Fetch a given User'''

        input_data = api.payload['data']
        points = {}
        data = {}
        for name in input_data.keys() :
            if 'checked' in input_data[name].keys() and input_data[name]['checked']:
                points[name] = float(input_data[name]['point'])
                res, code = eu_content.get(name)
                if code==200:
                    data[name] = res['_source']
                else:
                    print(res, code)

        G = create_graph(pre_create_graph(points=points, data=data)) 
        res = {'id': id, 'data':input_data, 'graph':{}}
        res['graph']['nodes'] = dict(G.nodes)
        res['graph']['edges'] = list(G.edges)

        return res, 200


# todo bulk api
# @ns_contents.route('/bulk')
# class ContentBulk(Resource):
#     '''Shows a list of all todos, and lets you POST to add new tasks'''
#     @ns_contents.doc('List_Contents')
#     @ns_contents.marshal_list_with(content)
#     def get(self):
#         '''List all tasks'''
#         # return DAO.Contents
#         return eu_content.get_all()
    
#     @ns_contents.expect(content)
#     @ns_contents.marshal_with(content)
#     def put(self, name):
#         '''Update a task given its identifier'''

#         #todo
#         # use wikiscraper class to get data
#         # post with name

#         res = eu_content.put(name)
#         return 


if __name__ == '__main__':
    app.run(debug=True)