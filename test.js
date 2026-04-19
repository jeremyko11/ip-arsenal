var r = {id: 'test123'};

// We need onclick="openMaterialDrawer('"+r.id+"')"
// So the HTML onclick attribute value should be: openMaterialDrawer('"+r.id+"')
// When JS evaluates this string: the ' are string delimiters, + is concat, r.id is variable
// Result: openMaterialDrawer('test123')

var onclick_value = "openMaterialDrawer('"+r.id+"')";
console.log('onclick_value:', onclick_value);

// Evaluate it
function openMaterialDrawer(x) { console.log('Called with:', x); }
eval(onclick_value);
