import logging
import sqlite3
import threading
import time
from collections import defaultdict
from threading import RLock

_thread_local = threading.local()

class NodesDatabase:
    _lock = RLock()
    _write_locks = {}
    _last_checkpoint = {}
    current_version = 3

    @staticmethod
    def get(device):
        with NodesDatabase._lock:
            global _thread_local
            dbs = getattr(_thread_local, 'dbs', None)
            if dbs is None:
                logging.warning(f"Creating dbs {_thread_local} {threading.get_ident()}")
                setattr(_thread_local, 'dbs', {})
                dbs = _thread_local.dbs
            if device not in NodesDatabase._write_locks:
                NodesDatabase._write_locks[device] = threading.Lock()
            if device not in NodesDatabase._last_checkpoint:
                NodesDatabase._last_checkpoint[device] = time.time()
            if device not in dbs:
                dbs[device] = NodesDatabase(device)
            return dbs[device]

    def __init__(self, device):
        import database

        self.write_lock = NodesDatabase._write_locks[device]
        self.db_path = f"{database.get_cache_dir()}/{device}-nodes.sqlite"
        logging.debug(f"Opening node database at {self.db_path} thread: {threading.get_ident()}")

        self.device = device
        self.conn = sqlite3.connect(self.db_path)
        self.init_db()

    def init_db(self):
        conn = self.conn
        cur = conn.cursor()
        cur.execute("PRAGMA user_version;")

        version = cur.fetchone()

        with conn:
            cur.execute("""
            CREATE TEMP TABLE IF NOT EXISTS tmp_node_ids (
                id   INTEGER PRIMARY KEY
            );            
            """)
            cur.execute("""
                        CREATE
                        TEMP TABLE IF NOT EXISTS tmp_node_names (
                name TEXT PRIMARY KEY
            );
            """)

        if len(version) == 0 or version[0] != NodesDatabase.current_version:
                with conn:
                    cur.execute(f"PRAGMA user_version = {NodesDatabase.current_version};")
                    conn.execute("PRAGMA foreign_keys = ON")
                    conn.execute('PRAGMA journal_mode=WAL;')
                    conn.execute('PRAGMA synchronous=NORMAL')

                    cur.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id   INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                has_full_data INTEGER NOT NULL DEFAULT 0 CHECK (has_full_data IN (0, 1))
            );
                    """)

                    try:
                        cur.execute("ALTER TABLE pips ADD COLUMN jumpwire INTEGER")
                    except sqlite3.OperationalError as e:
                        pass

                    # PIPs table:
                    # from_wire and to_wire are node IDs
                    # bidir = 0 (unidirectional) or 1 (bidirectional)
                    cur.execute("""
            CREATE TABLE IF NOT EXISTS pips (
                from_id INTEGER NOT NULL,
                to_id   INTEGER NOT NULL,
                bidir INTEGER NOT NULL CHECK (bidir IN (0,1)),
                jumpwire INTEGER NOT NULL CHECK (jumpwire IN (0,1)) DEFAULT 0,
                flags INTEGER NOT NULL DEFAULT 0,
                buffertype TEXT NOT NULL DEFAULT "",
                PRIMARY KEY (from_id, to_id),
                FOREIGN KEY (from_id) REFERENCES nodes(id),
                FOREIGN KEY (to_id)   REFERENCES nodes(id)
            ) WITHOUT ROWID;
                    """)

                    try:
                        cur.execute("""CREATE INDEX from_id_index ON pips (from_id);""")
                        cur.execute("""CREATE INDEX to_id_index ON pips (to_id);""")
                    except sqlite3.OperationalError as e:
                        pass


                    cur.execute("""
                    CREATE TABLE IF NOT EXISTS sites (
                        id   INTEGER PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        type TEXT NOT NULL,
                        x    INTEGER NOT NULL,
                        y    INTEGER NOT NULL
                    );
                    """)

                    cur.execute("""
        CREATE TABLE IF NOT EXISTS site_pins (
            site_id INTEGER NOT NULL,
            pin_name TEXT NOT NULL,
            node_id INTEGER NOT NULL,
        
            PRIMARY KEY (site_id, pin_name),
        
            FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
            FOREIGN KEY (node_id) REFERENCES nodes(id)
        ) WITHOUT ROWID;
                                """)


                    cur.execute("""
                    CREATE TABLE IF NOT EXISTS node_aliases (
                        node_id INTEGER NOT NULL,
                        alias TEXT UNIQUE NOT NULL,
                        
                        PRIMARY KEY (alias),
                        
                        FOREIGN KEY (node_id) REFERENCES nodes(id)
                    ) WITHOUT ROWID;            
                    """)

    def _populate_tmp(self, cur, type, values):
        cur.execute(f"DELETE FROM tmp_node_{type}s")

        cur.executemany(
            f"INSERT INTO tmp_node_{type}s ({type}) VALUES (?)",
            ((n,) for n in values)
        )

    def get_node_ids(self, names):
        conn = self.conn
        cur = conn.cursor()
        self._populate_tmp(cur, "name", names)

        cur.executemany(
            "INSERT OR IGNORE INTO nodes (name) VALUES (?)",
            ((ni,) for ni in names)
        )

        cur.execute(
            f"SELECT id, name FROM nodes where name IN (SELECT name from tmp_node_names)",
        )

        id_to_name = dict(cur.fetchall())
        name_to_id = {v: k for k, v in id_to_name.items()}
        return name_to_id

    def get_pips(self, filter = None, filter_type = None):
        conn = self.conn
        cur = conn.cursor()

        t = time.time()
        if filter is None:
            cur.execute(f"""
                SELECT n1.name, n2.name
                FROM pips p
                JOIN nodes n1 ON n1.id = p.from_id
                JOIN nodes n2 ON n2.id = p.to_id            
            """)
        elif filter_type is None:
            self._populate_tmp(cur, "name", filter)
            cur.execute(f"""
                SELECT n1.name, n2.name
                FROM pips p
                JOIN nodes n1 ON n1.id = p.from_id
                JOIN nodes n2 ON n2.id = p.to_id      
                WHERE n1.name IN (SELECT name from tmp_node_names) OR n2.name IN (SELECT name from tmp_node_names)      
            """)
        else:
            self._populate_tmp(cur, "name", filter)

            cur.execute(f"""
                SELECT n1.name, n2.name
                FROM pips p
                JOIN nodes n1 ON n1.id = p.from_id
                JOIN nodes n2 ON n2.id = p.to_id      
                WHERE {"n1" if filter_type == "from" else "n2"}.name IN (SELECT name from tmp_node_names)
            """)

        cnt = 0
        for from_id, to_id in cur.fetchall():
            yield from_id, to_id
            cnt = cnt + 1
        logging.debug(f"Returned {cnt} pips in {time.time()-t} seconds {cnt / (time.time()-t)} hz")

    def get_jumpwires(self):
        conn = self.conn
        cur = conn.cursor()

        cur.execute(f"""
            SELECT n1.name, n2.name, p.bidir, p.flags, p.buffertype
            FROM pips p
            JOIN nodes n1 ON n1.id = p.from_id
            JOIN nodes n2 ON n2.id = p.to_id
            WHERE jumpwire = 1
        """)

        for from_name, to_name, bidir, flags, bt in cur.fetchall():
            yield from_name, to_name

    def insert_jumpwires(self, jumpwires):
        conn = self.conn
        cur = conn.cursor()

        touched_names = set([w for ni in jumpwires for w in ni])

        cur.executemany(
            "INSERT OR IGNORE INTO nodes (name) VALUES (?)",
            ((ni,) for ni in touched_names)
        )

        self._populate_tmp(cur, "name", touched_names)

        cur.execute(
            f"SELECT id, name FROM nodes WHERE name IN (SELECT name from tmp_node_names)"
        )
        id_to_name = dict(cur.fetchall())
        name_to_id = {v: k for k, v in id_to_name.items()}

        cur.executemany(
            """
            INSERT OR IGNORE INTO pips (from_id, to_id, bidir, flags, buffertype) VALUES (?, ?, ?, ?, ?)
            """,
            [(name_to_id[j[0]], name_to_id[j[1]], 0, -1, "") for j in jumpwires]
        )

        cur.executemany(
            """
            UPDATE pips 
            SET jumpwire = 1
            WHERE from_id = ? AND to_id = ?
            """,
            [(name_to_id[j[0]], name_to_id[j[1]]) for j in jumpwires]
        )
        print("jmp", len(jumpwires))

        conn.commit()

    def get_node_data(self, names, skip_pips=False):
        from lapie import NodeInfo, PipInfo

        conn = self.conn
        cur = conn.cursor()
        cur.arraysize = 100000

        self._populate_tmp(cur, "name", names)

        cur.execute(
            f"SELECT id, name FROM nodes WHERE has_full_data = 1 and name IN (SELECT name from tmp_node_names)",
        )
        id_to_name = dict(cur.fetchall())
        name_to_id = {v:k for k,v in id_to_name.items()}

        # Prepare result dict
        result = {name: NodeInfo(name) for name in name_to_id}
        if skip_pips:
            return result

        for k,v in result.items():
            v.aliases.append(k)

        self._populate_tmp(cur, "id", list(id_to_name.keys()))

        cur.execute(f"""
            SELECT n1.name, n2.name, p.bidir, p.flags, p.buffertype
            FROM pips p
            JOIN nodes n1 ON n1.id = p.from_id
            JOIN nodes n2 ON n2.id = p.to_id
            WHERE p.from_id IN (SELECT id from tmp_node_ids) or
                  p.to_id IN (SELECT id from tmp_node_ids)
        """)

        t = time.time()
        cnt = 0
        while True:
            results = cur.fetchmany(cur.arraysize)
            if not results:
                break
            cnt = cnt + len(results)
            for from_name, to_name, bidir, flags, bt in results:
                pip = PipInfo(from_name, to_name,
                            is_bidi=bool(bidir),
                            flags=flags,
                            buffertype=bt)
                if from_name in result:
                    result[from_name].downhill_pips.append(pip)
                if to_name in result:
                    result[to_name].uphill_pips.append(pip)

        logging.debug(f"Looked up {cnt} pips in {time.time() - t} sec")

        cur.execute(f"""
            SELECT n.node_id, n.alias
            FROM node_aliases n
            WHERE n.node_id IN (SELECT id from tmp_node_ids)                      
        """)

        for node_id, alias in cur.fetchall():
            result[id_to_name[node_id]].aliases.append(alias)

        return result


    def insert_nodeinfos(self, nodeinfos):
        with self.write_lock:
            exception = None
            for i in range(3):
                try:
                    self._insert_nodeinfos(nodeinfos)

                    now = time.time()
                    if now - NodesDatabase._last_checkpoint[self.device] > 5 * 60:
                        NodesDatabase._last_checkpoint[self.device] = now
                        cur = self.conn.cursor()
                        logging.debug(f"Running wal checkpoint {threading.get_ident()}")
                        cur.execute("PRAGMA wal_checkpoint(FULL);")

                    return
                except sqlite3.OperationalError as e:
                    exception = e
            logging.warning(f"Could not insert nodeinfos after 3 tries: {exception}")

    def _insert_nodeinfos(self, nodeinfos):
        touched_names = set([w for ni in nodeinfos for p in ni.pips() for w in [p.to_wire, p.from_wire]]) | set(
            [n.name for n in nodeinfos])


        with self.conn as conn:
            cur = conn.cursor()

            # 1. Insert all nodes
            cur.executemany(
                "INSERT OR IGNORE INTO nodes (name) VALUES (?)",
                ((ni,) for ni in touched_names)
            )

            self._populate_tmp(cur, "name", {n.name for n in nodeinfos})

            cur.execute(
                f"""
                    UPDATE nodes
                    SET has_full_data = 1
                    WHERE name IN (SELECT name from tmp_node_names)
                    """
            )

            self._populate_tmp(cur, "name", touched_names)

            cur.execute(
                f"SELECT id, name FROM nodes WHERE name IN (SELECT name from tmp_node_names)"
            )
            id_to_name = dict(cur.fetchall())
            name_to_id = {v:k for k,v in id_to_name.items()}

            pip_rows = []

            for ni in nodeinfos:
                for p in ni.pips():
                    from_id = name_to_id.get(p.from_wire)
                    to_id = name_to_id.get(p.to_wire)

                    pip_rows.append(
                        (from_id, to_id,
                         1 if p.is_bidi else 0,
                         p.flags,
                         p.buffertype)
                    )

            cur.executemany(
                """
                INSERT OR IGNORE INTO pips
                (from_id, to_id, bidir, flags, buffertype)
                VALUES (?, ?, ?, ?, ?)
                """,
                pip_rows
            )

            cur.executemany(
                """
                INSERT OR IGNORE INTO node_aliases
                (node_id, alias)
                VALUES (?, ?)
                """,
                [(name_to_id[n.name], alias) for n in nodeinfos for alias in n.aliases if alias != n.name]
            )

    def insert_sites_and_fetch_ids(self, sites):
        if not sites:
            return {}

        with self.conn:
            cur = self.conn.cursor()

            self._populate_tmp(cur, "name", {s for s in sites})

            cur.execute("""
                        INSERT INTO sites (name)
                        SELECT t.name
                        FROM tmp_node_names t
                                 LEFT JOIN sites s ON s.name = t.name
                        WHERE s.name IS NULL
                        """)

            rows = cur.execute("""
                               SELECT s.name, s.id
                               FROM sites s
                                        JOIN tmp_names t ON t.name = s.name
                               """).fetchall()

        return dict(rows)

    def insert_sites(self, sites):
        conn = self.conn
        cur = conn.cursor()

        # ---- Insert sites ----
        site_rows = [
            (name,
             data["type"],
             int(data["x"]),
             int(data["y"]))
            for name, data in sites.items()
        ]

        cur.executemany(
            """
            INSERT OR IGNORE INTO sites (name, type, x, y)
            VALUES (?, ?, ?, ?)
            """,
            site_rows
        )

        site2id = dict(cur.execute("""
                           SELECT s.name, s.id
                           FROM sites s
                           """).fetchall())

        # ---- Resolve node IDs (from pin_node) ----
        node_names = {
            pin["pin_node"]
            for data in sites.values()
            for pin in data["pins"]
        }

        node2id = self.get_node_ids(node_names)

        # ---- Insert pins ----
        pin_rows = []

        for site_name, data in sites.items():
            sid = site2id[site_name]

            for pin in data["pins"]:
                nid = node2id.get(pin["pin_node"])
                if nid is None:
                    continue  # or raise if missing nodes are an error

                pin_rows.append(
                    (sid, pin["pin_name"], nid)
                )

        cur.executemany(
            """
            INSERT OR IGNORE INTO site_pins
            (site_id, pin_name, node_id)
            VALUES (?, ?, ?)
            """,
            pin_rows
        )

        conn.commit()

    def get_sites(self):
        conn = self.conn
        cur = conn.cursor()
        result = {}

        # ---- Fetch sites ----
        cur.execute(
            f"""
            SELECT id, name, type, x, y
            FROM sites
            """,
        )

        site_rows = cur.fetchall()
        if not site_rows:
            return result

        site_id = {}
        for sid, name, typ, x, y in site_rows:
            site_id[sid] = name
            result[name] = {
                "type": typ,
                "x": x,
                "y": y,
                "pins": []
            }

        # ---- Fetch pins ----
        cur.execute(
            f"""
            SELECT sp.site_id, sp.pin_name, n.name
            FROM site_pins sp
            JOIN nodes n ON n.id = sp.node_id
            """,
        )

        for sid, pin_name, node_name in cur.fetchall():
            result[site_id[sid]]["pins"].append({
                "pin_name": pin_name,
                "pin_node": node_name
            })

        return result
