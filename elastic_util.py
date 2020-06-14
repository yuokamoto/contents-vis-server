#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.INFO)

from elasticsearch import Elasticsearch
from elasticsearch.client import IndicesClient
from elasticsearch.exceptions import NotFoundError, RequestError

# es = Elasticsearch()

INDEX_NAMES = ['contents', 'users']

class ElasticUtil(object):
    def __init__(self, index, host='localhost', port=9200, scheme='https', http_auth=('elastic', ''), doc_type='_doc', field_limit=5000):
        self._client = Elasticsearch(host=host, port=port, scheme=scheme, http_auth=http_auth)
        self._doc_type = doc_type
        self._index = index

        self._index_client = IndicesClient(self._client) 
        if self._index_client.exists(index=self._index):
            logging.warning('index name:'+self._index+' exists')
        else:
            logging.info('create index name:'+self._index)
            body = {
                "settings": {
                    "index.mapping.total_fields.limit": field_limit
                },
            }
            self._index_client.create(index=self._index)

    def get(self, id):
        exists = self._client.exists(index=self._index, id=id)
        if exists:
            res = self._client.get(index=self._index, id=id)
            return res, 200
        else:
            logging.error(id+' not found')
            return False, 404

    def get_all(self):
        search_query = {
            "query": {
                "match_all": {}
            }
        }
        res = self._client.search(index=self._index, body=search_query)
        return res['hits']['hits'], 200

    def post(self, body={}):
        if type(body)!=dict:
            msg = 'Body must be dictionary'
            logging.error(msg)
            return msg, 400

        res_dict = body
        # res_dict = body = {"ウンナンさん": {"point": 0.2, "checked": 1.0, "id": -1.0},
        #                      "ウンナンの気分は上々。": {"point": 0.2, "checked": 1.0, "id": -1.0},
        #                      "UN街": {"point": 0.2, "checked": 1.0, "id": -1.0},
        #                      "勇者ヨシヒコと魔王の城": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "勇者ヨシヒコと悪霊の鍵": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "勇者ヨシヒコと導かれし七人": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "ネリさまぁ〜ず": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "神さまぁ〜ず": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "ホリさまぁ〜ず": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "マルさまぁ〜ず": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "バナナ塾": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "バナナマンのブログ刑事": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "オトナ養成所_バナナスクール": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "ツギクルもん": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "うつけもん": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "オサレもん": {"point": 0.25, "checked": 1.0, "id": -1.0},
        #                      "30minutes": {"point": 0.33, "checked": 1.0, "id": -1.0},
        #                      "30minutes鬼": {"point": 0.33, "checked": 1.0, "id": -1.0},
        #                      "デリパンダ〜おしゃべりデリ坊、東京ド真ん中配達中〜": {"point": 0.33, "checked": 1.0, "id": -1.0},
        #                      "あらびき団": {"point": 0.5, "checked": 1.0, "id": -1.0},
        #                      "タイプライターズ": {"point": 0.5, "checked": 1.0, "id": -1.0},
        #                      "飛び出せ!科学くん": {"point": 0.5, "checked": 1.0, "id": -1.0},
        #                      "ラブレターズのオールナイトニッポン0(ZERO)": {"point": 0.6, "checked": 1.0, "id": -1.0}
        #                      }
        res = self._client.index(index=self._index, body=res_dict, doc_type=self._doc_type)
        logging.info('id: '+res['_id']+' was created')
        return res, 201

    def put(self, id, body={}): 
        if type(body)!=dict:
            msg = 'Body must be dictionary'
            logging.error(msg)
            return msg, 400

        exist = self._client.exists(index=self._index, id=id)
        res = self._client.index(id=id, index=self._index, body=body, doc_type=self._doc_type)
        if exist:
            logging.info(id+' was updated')            
        else:
            logging.info(id+' was created')            

        return res, 200

class ElasticUtilNameId(ElasticUtil):
    def __init__(self, index, host='localhost', port=9200, scheme='https', http_auth=('elastic', ''), doc_type='_doc', field_limit=5000):
        super().__init__(index, host=host, port=port, scheme=scheme, http_auth=http_auth, doc_type=doc_type, field_limit=field_limit)

    def name_check(self, name):
        if name is '':
            msg = 'Empty name is not allowed'
            logging.error(msg)
            return msg, 400
        else:
            return '', 200

    def get(self, name):
        search_query = {
          "query": {
            "term": {
              "name.keyword": name
            }
          }
        }
        res = self._client.search(index=self._index, body=search_query)['hits']['hits']
        if len(res)>1:
            # for data in res:
            #     print(data['_id'])
            #     res = self._client.delete(id=data['_id'], index=self._index, doc_type=self._doc_type)
            msg = 'There are multiple contents with same name: ' + name + '. Please fix the data'
            logging.error(msg)
            return msg, 500
        elif len(res)==0:
            msg = name+' not found'
            logging.error(msg)
            return msg, 404
        else:
            return res[0], 200

    def get_list(self, names):
        res = []
        for name in names:
            res.append(self.get(name))[0]
        return res, 200

    def get_all(self):
        search_query = {
            "query": {
                "match_all": {}
            }
        }
        res = self._client.search(index=self._index, body=search_query)
        return res['hits']['hits'], 200

    def post(self, name, body={}):
        res, code = self.name_check(name)
        if code==400:
            return msg, code
        res, code = self.get(name)
        if code==200:
            msg = name+' is exist'
            logging.warn(msg)
            return msg, 400
        if type(body)!=dict:
            msg = 'Body must be dictionary'
            logging.error(msg)
            return msg, 400

        res_dict = body
        res_dict['name'] = name
        res = self._client.index(index=self._index, body=res_dict, doc_type=self._doc_type)
        logging.info(name+' was created')
        return res, 201

    def put(self, name, body={}):
        msg, code = self.name_check(name)
        if code==400:
            return msg, code
        if type(body)!=dict:
            msg = 'Body must be dictionary'
            logging.error(msg)
            return msg, 400

        res = self.get(name)
        res_dict = body
        res_dict['name'] = name

        res, code = self.get(name)
        try:
            print(body, res, code)
            if code==200:
                doc_id = res['_id']
                # res = self._client.delete(id=doc_id, index=self._index, doc_type=self._doc_type, reflesh=True)
                res = self._client.index(id=doc_id, index=self._index, body=res_dict, doc_type=self._doc_type)
                logging.info(name+' was updated')
                return res, 200
            elif code==404:
                res = self._client.index(index=self._index, body=res_dict, doc_type=self._doc_type)
                logging.info(name+' was created')            
                return res, 201
            elif code==500:
                return res, code
        except RequestError as err:
            logging.error(err)
            return 'Elasticsearch RequestError', 500




if __name__ == "__main__":
    # Initial setup for elasticsearch
    eu_user = ElasticUtil(index=INDEX_NAMES[1])
    eu_contents = ElasticUtilNameId(index=INDEX_NAMES[0])
    # print(eu.post('test'))
    # print(eu.put('test'))
    # print(eu.put('test2'))
    # print(eu.get('2'))
    # print(eu.get('test'))

    # print(eu.get_all())