import logging
import os
from flask import Flask
from flask import Blueprint
from flask import request
from be.view import auth
from be.view import seller
from be.view import buyer
# from be.model.store import init_database
import time
from threading import Timer
from be.model import store
from be.model import error
from init_db.ConnectDB import Session
bp_shutdown = Blueprint("shutdown", __name__)


def shutdown_server():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()


@bp_shutdown.route("/shutdown")
def be_shutdown():
    shutdown_server()
    return "Server shutting down..."


def be_run():
    this_path = os.path.dirname(__file__)
    parent_path = os.path.dirname(this_path)
    log_file = os.path.join(parent_path, "app.log")
    # init_database()

    logging.basicConfig(filename=log_file, level=logging.ERROR)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
    )
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)

    app = Flask(__name__)
    app.register_blueprint(bp_shutdown)
    app.register_blueprint(auth.bp_auth)
    app.register_blueprint(seller.bp_seller)
    app.register_blueprint(buyer.bp_buyer)
    delete_order(10)
    app.run(debug=True, use_reloader=False)


def delete_order(seconds):
    # Session = store.get_db_conn()
    cursor = Session.execute("SELECT order_id, state, create_time FROM new_order;")
    for row in cursor:
        order_id = row[0]
        print(order_id)
        create_time = row[2]
        state = row[1]
        # 若超时且状态为未付款
        if (time.time() - create_time >= 60 and state == 0):
            # 增加库存
            cur = Session.execute("SELECT store_id FROM new_order WHERE order_id = ?;", (order_id,))
            row = cur.fetchone()
            if row is None:
                return error.error_invalid_order_id(order_id)
            print(row)
            store_id = row[0]
            print(store_id)
            cur = Session.execute("SELECT book_id, count FROM new_order_detail WHERE order_id = ?;", (order_id,))
            for row in cur:
                book_id = row[0]
                count = row[1]
                Session.execute(
                    "UPDATE store set stock_level = stock_level + ? "
                    "WHERE store_id = ? and book_id = ? ; ",
                    (count, store_id, book_id))
            Session.execute("Delete FROM new_order WHERE order_id = ?;", (order_id,))
            Session.execute("Delete FROM new_order_detail WHERE order_id = ?;", (order_id,))
    Session.commit()
    t = Timer(seconds, delete_order, (seconds,))
    t.start()
