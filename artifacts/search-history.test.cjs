const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const html = readFileSync(`${__dirname}/Лента новостей v9.dc.html`, 'utf8');
const script = html.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/)[1];
const storage = new Map();
const Component = runInNewContext(`${script}; Component`, {
  window: { localStorage: {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
  } },
  DCLogic: class {
    props = {};
    setState(patch) { Object.assign(this.state, typeof patch === 'function' ? patch(this.state) : patch); }
  },
});
let app = new Component();
assert.equal(typeof app.rememberSearch, 'function');
assert.equal(app.searchVals().searchCompanies.length, 0, 'No company recommendations on empty search');
app.searchVals().onSearch({ target: { value: 'РЖД' } });
assert.equal(app.state.searchHistory.length, 0, 'Typing does not write history');
app.searchVals().onSearchKey({ key: 'Enter', isComposing: true, preventDefault() {} });
assert.equal(app.state.searchHistory.length, 0, 'IME confirmation does not submit');
app.searchVals().onSearchKey({ key: 'Enter', preventDefault() {} });
assert.deepEqual(Array.from(app.state.searchHistory), ['РЖД']);
app.rememberSearch('  цены   стали  ');
app.rememberSearch('ржд');
assert.deepEqual(Array.from(app.state.searchHistory), ['ржд', 'цены стали']);
app.rememberSearch('   ');
assert.equal(app.state.searchHistory.length, 2);
app = new Component();
assert.deepEqual(Array.from(app.state.searchHistory), ['ржд', 'цены стали'], 'History survives new instance');
app.searchVals().searchHistoryRows[1].pick();
assert.equal(app.state.searchQ, 'цены стали');
assert.equal(app.state.searchHistory[0], 'цены стали');
app.searchVals().clearSearch();
app.searchVals().searchHistoryRows[0].remove();
assert.deepEqual(Array.from(app.state.searchHistory), ['ржд']);
for (let i = 0; i < 12; i++) app.rememberSearch(`запрос ${i}`);
assert.equal(app.state.searchHistory.length, 10);
assert.equal(app.state.searchHistory[9], 'запрос 2');
app.searchVals().clearSearchHistory();
assert.equal(new Component().state.searchHistory.length, 0);
app.searchVals().onSearch({ target: { value: 'РЖД' } });
app.searchVals().searchNews[0].onClick();
assert.equal(app.state.searchHistory[0], 'РЖД', 'Opening result saves query');
const key = [...storage.keys()][0];
storage.set(key, '{bad json');
assert.equal(new Component().state.searchHistory.length, 0);
storage.set(key, JSON.stringify([null, 42, {}, '  РЖД ', 'ржд', '', 'сталь']));
assert.deepEqual(Array.from(new Component().state.searchHistory), ['РЖД', 'сталь']);
console.log('Search history checks passed');
