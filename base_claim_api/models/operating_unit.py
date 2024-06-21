# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import odoorpc

class Operatingunit(models.Model):
    _inherit = 'operating.unit'

    host = fields.Char(
        string='Host / URL',
        required=False)
    database = fields.Char(
        string='Database',
        required=False)
    username = fields.Char(
        string='Username',
        required=False)
    password = fields.Char(
        string='Password',
        required=False)
    port = fields.Char(
        string='Port',
        required=False)

    host_bis = fields.Char(
        string='Host / URL',
        required=False)
    database_bis = fields.Char(
        string='Database',
        required=False)
    username_bis = fields.Char(
        string='Username',
        required=False)
    password_bis = fields.Char(
        string='Password',
        required=False)
    port_bis = fields.Char(
        string='Port',
        required=False)

    @api.multi
    def check_config(self, type):
        """
        :param type: odoo, bis
        :return:
        """
        self.ensure_one()
        if type == 'odoo':
            if self.host and self.database and self.username and self.password and self.port :
                return True
        else :
            if self.host_bis and self.database_bis and self.username_bis and self.password_bis and self.port_bis :
                return True
        raise UserError(_('API configuration for %s is not correctly set. Please make sure that you have input all configuration.'%(self.display_name)))
    
    @api.multi
    def connect_to_bis(self):
        self.ensure_one()
        self.check_config('bis')
        cursor, connection = self.env.user.connect_to_mysql(
            host=self.host_bis,
            database=self.database_bis,
            user=self.username_bis,
            password=self.password_bis,
            port=self.port_bis
        )
        return cursor, connection
    
    @api.multi
    def test_connection_bis(self):
        cursor, connection = self.connect_to_bis()
        cursor.close()
        connection.close()
        raise UserError(_('Connection succesfully'))

    @api.multi
    def connect_to_odoo(self):
        self.ensure_one()
        self.check_config('odoo')
        res = self.env.user.connect_to_odoo(
            host=self.host,
            port=self.port,
            db=self.database,
            login=self.username,
            password=self.password
        )
        return res

    @api.multi
    def test_connection(self):
        self.connect_to_odoo()
        raise UserError(_('Connection succesfully'))
