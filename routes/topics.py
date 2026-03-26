from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3
import hashlib

bp = Blueprint('topics', __name__)