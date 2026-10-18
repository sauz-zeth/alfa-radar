const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const html = readFileSync(`${__dirname}/Лента новостей v9.dc.html`, 'utf8');
const script = html.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/)[1];
const app = runInNewContext(`${script}; new Component()`, {
  DCLogic: class {
    props = {};
    setState(patch) { Object.assign(this.state, typeof patch === 'function' ? patch(this.state) : patch); }
  },
});
assert.equal(typeof app.searchVals, 'function', 'Global search must be available');
const search = q => { app.state.searchQ = q; return app.searchVals(); };
assert.equal(search('  рЖд  ').searchNews[0].id, 'n3');
assert.equal(search('РЖД').searchCompanies[0].name, 'РЖД');
assert.ok(search('таможенной стоимости').searchNews.some(n => n.id === 'n1'));
assert.ok(search('форум').searchNews.length, 'Hidden news are searchable');
assert.equal(search('несуществующаякомпания').searchEmpty, true);
assert.equal(search('   ').searchInitial, true);
app.state.tags = ['Важное упоминание'];
assert.deepEqual(Array.from(app.vq()), ['n3'], 'Only direct mentions, not general business impact');
app.state.tags = ['Важное упоминание', 'Логистика'];
assert.deepEqual(Array.from(app.vq()), ['n3']);
app.state.tags = ['Важное упоминание', 'Пошлины'];
assert.deepEqual(Array.from(app.vq()), [], 'Topic must not bypass the direct mention filter');
app.state.tags = ['Пошлины'];
assert.deepEqual(Array.from(app.vq()), ['n1'], 'Existing topic filter still works');
app.state.tags = [];
assert.equal(app.vq().length, 5, 'Clearing filters restores all news');
app.state.tags = ['несуществующий тег'];
app.state.queue = [];
assert.equal(search('РЖД').searchNews[0].id, 'n3', 'Search ignores feed filters');
search('РЖД').searchCompanies[0].onClick();
assert.equal(app.searchVals().searchNews[0].id, 'n3');
app.state.searchOpen = true;
app.searchVals().searchNews[0].onClick();
assert.equal(app.state.news, 'n3');
assert.equal(app.state.searchOpen, true, 'Keep search for return from detail');
app.searchVals().clearSearch();
assert.equal(app.searchVals().searchInitial, true);
console.log('Search and feed filter checks passed');
