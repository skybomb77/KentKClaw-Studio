const fs = require('fs');
let content = fs.readFileSync('index.html', 'utf8');
// Target the exact corrupted string
const corrupted = '<div class="input-group" style="margin-top: 24px; padding-top: 12px;">\\r\\n                    <label>Resolution Quality</label>';
const fixed = '<div class="input-group" style="margin-top: 24px;">\n                    <label>Resolution Quality</label>';

if (content.includes(corrupted)) {
    content = content.replace(corrupted, fixed);
    fs.writeFileSync('index.html', content, 'utf8');
    console.log('SUCCESS: Corrupted line fixed.');
} else {
    // Fallback search
    console.log('Searching via regex...');
    content = content.replace(/style="margin-top: 24px; padding-top: 12px;">\\r\\n\s*<label>/g, 'style="margin-top: 24px;">\n                    <label>');
    fs.writeFileSync('index.html', content, 'utf8');
    console.log('Done with regex.');
}
