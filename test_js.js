<!DOCTYPE html>
<html>
<body>
<div id="test" onclick="openMaterialDrawer(\''+r.id+'\')">click me</div>
<script>
var r = {id: 'MYID'};
// What happens when we click:
// The onclick string value is: openMaterialDrawer(\''+r.id+'\')
// Let me simulate:
var attr = "openMaterialDrawer(\''+r.id+'\')";
console.log("attr:", attr);

// Parse it
var simulated = "openMaterialDrawer(\'"+r.id+"\')";
console.log("simulated:", simulated);

// Try the actual call
function openMaterialDrawer(x) { console.log("Called:", x); }
try {
    eval("(" + simulated + ")");
} catch(e) {
    console.log("Error:", e.message);
}
</script>
</body>
</html>
