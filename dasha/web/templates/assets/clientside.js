if (!window.dash_clientside) {window.dash_clientside = {};}
window.dash_clientside.tolteca = {
    interface_from_latest_data: function(changed, data, interface_options) {
        console.log(changed)
        if (!changed || !data) {
            return interface_options
        }
        options = [];
        data[0]['RoachIndex'].split(',').forEach(
            e => options.push({
                'label': "toltec" + e,
                'value': parseInt(e)
                })
        )
        return options
    },
    array_summary: function(a, s) {
        // console.log("summary")
        // console.log(a)
        // console.log(s)
        if (a) {
            return {
                ...s,
                'size': a.length,
                'first': a[0]
                }
        }
        return s
    },
    array_concat: function(a, b) {
        // console.log("concat")
        // console.log(a)
        // console.log(b)
        if (!a || a.length == 0) {
            // console.log("no update")
            return b
        }
        return a.concat(b)
    },
}


// https://community.plot.ly/t/links-in-datatable-multipage-app/26081/6
window.dash_clientside.ui = {
    activateNavlink: function(pathname, navitems_, state) {

        if (pathname === '/') {
            pathname = state['navlink_default']
        }
        navitems = navitems_.map(a => ({...a}));
        navitems.forEach(function(navitem) {
            navitem.props.active = (pathname === navitem.props.href)
        })
        return navitems
    },
    collapseWithClick: function(n, classname) {
        if (n) {
            if (classname && classname.includes(" collapsed")) {
                return classname.replace(" collapsed", "")
            }
            return classname + " collapsed"
        }
        return classname
    },
    toggleWithClick: function(n, is_open) {
        if (n)
            return !is_open
        return is_open
    },
    replaceWithLinks: function(trigger, table_id) {
        let cells = document.getElementById(table_id)
            .getElementsByClassName("dash-cell column-1");
        base_route = "/"

        cells.forEach((elem, index, array) => {
            elem.children[0].innerHTML =
                '<a href="' +
                base_route +
                elem.children[0].innerText +
                '" target="_some_target" rel="noopener noreferrer">' +
                elem.children[0].innerText +
                "</a>";
        });
        return null;
    }
}

window.dash_clientside.datastore = {
    getKey: function(data, key) {
        console.log("get " + key + " from " + data)
        return data[key]
    },
}


window.dash_clientside.syncedlist = {
    updateMeta: function(data, meta) {
        console.log("update meta")
        console.log(meta)
        console.log(data)
        if (data) {
            return {
                ...meta,
                'size': data.length,
                'pk_latest': data[0][meta.pk]
                }
        }
        return meta
    },
    update: function(new_data, old_data, meta) {
        console.log("update data")
        console.log(new_data)
        console.log(old_data)
        console.log(meta)
        if (!new_data || new_data.length == 0) {
            // console.log("no update")
            return old_data
        }
        // no old data
        if (!old_data || old_data.length == 0) {
            return new_data
        }
        // merge data
        return new_data.concat(old_data)
    },
}
