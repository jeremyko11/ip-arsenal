var r = {id: 'TEST123'};

// What does the onclick expression need to be?
// We need to call: openMaterialDispatcher('TEST123')
// Which is JavaScript: openMaterialDispatcher( + ' + TEST123 + ' + )
// Where ' is the single-quote character

// In the HTML onclick attribute (double-quoted), the JS expression is:
// openMaterialDispatcher('TEST123')
// Where ' are SINGLE QUOTE characters in the HTML

// As a JS string literal (for the onclick attribute value), we need:
// The string: 'TEST123'
// Which is: single-quote + TEST123 + single-quote

// In a JS double-quoted string literal:
// var js_str = "'"+r.id+"'";  // ' + r.id + '
// This is: quote, single-quote, quote, +, r.id, +, quote, single-quote, quote
// = 9 chars

var js_str = "'"+r.id+"'";  // This is: ' + TEST123 + '
console.log("js_str =", js_str);
console.log("js_str chars:", [...js_str].map(c => c.charCodeAt(0)));

// The full onclick expression:
var expr = "openMaterialDispatcher(" + js_str + ")";
console.log("expr =", expr);

// Test it:
function openMaterialDispatcher(x) {
    console.log("Called with:", x);
}
eval(expr);

// So in the HTML attribute (double-quoted), we need:
// onclick="openMaterialDispatcher('"+r.id+"')"
// Where the JS code is: openMaterialDispatcher('"+r.id+"')

// When the HTML parser reads this, the JS code is:
// openMaterialDispatcher('"+r.id+"')
// Where ' are single-quote characters in the JS code

// As a string (in Python/HTML), we need to ESCAPE the single quotes in the JS code
// For HTML attribute (double-quoted), we escape " with &quot; but for JS in onclick, we use \"

// The JS string 'TEST123' in an HTML onclick attribute value would be written as:
// onclick="openMaterialDispatcher(\'TEST123\')"
// Where \' is an escaped single-quote in HTML context.

// But wait! In HTML (not in JS), \' is NOT an escape sequence!
// So onclick="openMaterialDispatcher(\'TEST123\')" is NOT valid HTML!

// Actually, in HTML, the only escape is &xxx; for special characters.
// Backslash in HTML is just a literal backslash!

// So to have ' in the JS code inside an HTML double-quoted attribute,
// we just write ' directly. No escaping needed.

// onclick="openMaterialDispatcher('TEST123')"
// This has: onclick=" (HTML), openMaterialDispatcher( (JS), ' (JS single-quote), TEST123, ' (JS single-quote), ) (JS), " (HTML close)

// Let me verify in HTML:
// <div onclick="openMaterialDispatcher('TEST')"> - this works!
// The HTML parser gives the attribute value: openMaterialDispatcher('TEST')
// JS evaluates this: openMaterialDispatcher( + 'TEST' + ) = openMaterialDispatcher('TEST')

// So the CORRECT HTML is:
// onclick="openMaterialDispatcher('"+r.id+"')"
// Where ' is just a regular single-quote in the HTML source

// In the file, this is written as:
// onclick="openMaterialDispatcher('"+r.id+"')"
// (no escaping needed for ' in HTML double-quoted attribute)

// But the BROKEN version has:
// onclick="openMaterialDispatcher(\'"+r.id+"\')"
// Where \' is backslash-single-quote (2 chars in the file)
// When HTML parses this, it gives: openMaterialDispatcher(\'"+r.id+"\')
// Which JS evaluates: \' = ' (ignored backslash), \" = " (also ignored backslash since \" not valid JS escape)
// Wait no! In JS, \" IS a valid escape (produces "), and \' also produces '

// Let me test in Node:
var broken = "\\'"+r.id+"\"";  // \' + TEST123 + "
console.log("broken =", broken);
