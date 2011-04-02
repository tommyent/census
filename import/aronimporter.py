#!/usr/bin/env python
import psycopg2
import csv
import urllib
from os import listdir
import os.path
from lib import STATES
import re

class Importer:
    def __init__(self, geo_level="tract"):
        DB_CONNECT_STRING = "dbname=censusweb user=censusweb"
        self.conn = psycopg2.connect(DB_CONNECT_STRING)
        self.cur = self.conn.cursor()
        self.table_name = geo_level + "_data_2000"
        
    def import_data(self):
        self._drop_old_tables()
        data_and_headers = self._get_file_heads()
        fields_and_values = self._tablize_headers(data_and_headers)
        create_sql = "create table %s (%s)" % (self.table_name, ",".join(fields_and_values["fields"]))
        self.cur.execute(create_sql)
        self.conn.commit()
        self._insert_data(fields_and_values)
        
    def fetch_crosswalk(self):
        urllib.urlretrieve ("http://www.census.gov/geo/www/2010census/tract_rel/trf_txt/us2010trf.txt", "./data/cross.txt")
        
    #private methods
    def _insert_data(self,fields_and_values):
        insert_sql = "insert into " + self.table_name + " (" + ",".join(fields_and_values['headers']) + ")"
        for file in filter(lambda x: x.endswith(".tsv"), listdir("./data")):
            cur_file = "Working on file %s" % file
            reader = csv.reader(open(os.path.join("./data",file)), delimiter='\t')
            header = reader.next()
            for i,line in enumerate(reader):
                values = ",".join(self._string_or_num(fields_and_values, line))
                self.cur.execute(insert_sql + " values (" + values + ")")
                self.conn.commit()
                print cur_file + "\tline %s" % str(i)
        
    def _string_or_num(self,fields_and_values,line):
        results = []
        for i,type in enumerate(fields_and_values["types"]):
            if type == "s":
                results.append("'" + line[i] + "'")
            else:
                results.append(line[i])
        return results
            
    def _get_file_heads(self):
        file_name = filter(lambda x: x.endswith(".tsv"), listdir("./data"))
        reader = csv.reader(open(os.path.join("./data",file_name[0])), delimiter='\t')
        header_line = reader.next()
        data_line = reader.next()
        if (header_line and data_line) and (len(header_line) == len(data_line)):
            return {"fields":[], "headers":header_line, "data_line":data_line, "types":[]}
        else:
            raise Exception("No data files or data doesn't match")
            
    def _tablize_headers(self, data_and_headers):
        special_headers = ["Summary_Level", "Geographic_Component", "State_FIPS", "Place_FIPS", "County_FIPS", "Tract", "Zip", "Block", "Name"]
        for i,node in enumerate(data_and_headers["data_line"]):
            header = data_and_headers["headers"][i]
            data_and_headers["headers"][i] = header.replace(" ", "_")
            if node in special_headers:
                data_and_headers["fields"].append(header.replace(" ", "_") + " VARCHAR(255)")
                data_and_headers["types"].append("s")
            elif re.search('^-?\d+\.\d+$', node):
                data_and_headers["fields"].append(header.replace(" ", "_") + " NUMERIC(11,6)")
                data_and_headers["types"].append("n")
            elif node.isdigit() and not re.search('^0', node):
                data_and_headers["fields"].append(header.replace(" ", "_") + " INTEGER")
                data_and_headers["types"].append("i")
            else:
                data_and_headers["fields"].append(header.replace(" ", "_") + " VARCHAR(255)")
                data_and_headers["types"].append("s")
        return data_and_headers
            
    def _drop_old_tables(self):
        self.cur.execute("drop table if exists %s" % self.table_name)
        self.conn.commit()