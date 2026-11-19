(() => {
    const selector = '.st-key-search_fields [data-testid="stTextInput"] input[type="text"]';
    if (window.itemSearchKoreanInputInstalled) return;
    window.itemSearchKoreanInputInstalled = true;

    const keys = {
        r: 'ㄱ', R: 'ㄲ', s: 'ㄴ', e: 'ㄷ', E: 'ㄸ', f: 'ㄹ', a: 'ㅁ',
        q: 'ㅂ', Q: 'ㅃ', t: 'ㅅ', T: 'ㅆ', d: 'ㅇ', w: 'ㅈ', W: 'ㅉ',
        c: 'ㅊ', z: 'ㅋ', x: 'ㅌ', v: 'ㅍ', g: 'ㅎ',
        k: 'ㅏ', o: 'ㅐ', i: 'ㅑ', O: 'ㅒ', j: 'ㅓ', p: 'ㅔ', u: 'ㅕ',
        P: 'ㅖ', h: 'ㅗ', y: 'ㅛ', n: 'ㅜ', b: 'ㅠ', m: 'ㅡ', l: 'ㅣ',
    };
    const initials = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
    const vowels = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ';
    const finals = ' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ';
    const vowelPairs = {
        'ㅗㅏ': 'ㅘ', 'ㅗㅐ': 'ㅙ', 'ㅗㅣ': 'ㅚ',
        'ㅜㅓ': 'ㅝ', 'ㅜㅔ': 'ㅞ', 'ㅜㅣ': 'ㅟ', 'ㅡㅣ': 'ㅢ',
    };
    const finalPairs = {
        'ㄱㅅ': 'ㄳ', 'ㄴㅈ': 'ㄵ', 'ㄴㅎ': 'ㄶ', 'ㄹㄱ': 'ㄺ', 'ㄹㅁ': 'ㄻ',
        'ㄹㅂ': 'ㄼ', 'ㄹㅅ': 'ㄽ', 'ㄹㅌ': 'ㄾ', 'ㄹㅍ': 'ㄿ', 'ㄹㅎ': 'ㅀ', 'ㅂㅅ': 'ㅄ',
    };
    const splitFinal = Object.fromEntries(Object.entries(finalPairs).map(([pair, final]) => [final, pair]));

    function compose(letters) {
        let text = '', initial = '', vowel = '', final = '';
        function commit() {
            if (initial && vowel) {
                const index = (initials.indexOf(initial) * 21 + vowels.indexOf(vowel)) * 28;
                text += String.fromCharCode(0xac00 + index + finals.indexOf(final || ' '));
            } else {
                text += initial + vowel;
            }
            initial = vowel = final = '';
        }
        for (const letter of letters) {
            const jamo = keys[letter] || keys[letter.toLowerCase()];
            if (vowels.includes(jamo)) {
                if (final) {
                    const [remain, move] = splitFinal[final] || ['', final];
                    final = remain;
                    commit();
                    initial = move;
                } else if (vowelPairs[vowel + jamo]) {
                    vowel = vowelPairs[vowel + jamo];
                    continue;
                } else if (vowel) {
                    commit();
                }
                vowel = jamo;
            } else if (initial && vowel && !final && finals.includes(jamo)) {
                final = jamo;
            } else if (finalPairs[final + jamo]) {
                final = finalPairs[final + jamo];
            } else {
                commit();
                initial = jamo;
            }
        }
        commit();
        return text;
    }

    const drafts = new WeakMap();
    const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    document.addEventListener('compositionstart', event => drafts.delete(event.target), true);
    document.addEventListener('keydown', event => {
        const input = event.target;
        if (!(input instanceof HTMLInputElement) || !input.matches(selector)) return;
        const previous = drafts.get(input);
        const continuing = previous && previous.value === input.value
            && input.selectionStart === previous.end && input.selectionEnd === previous.end;
        const typing = /^[a-z]$/i.test(event.key);
        const deleting = event.key === 'Backspace' && continuing;
        if (event.ctrlKey || event.metaKey || event.altKey || event.isComposing
                || event.keyCode === 229 || (!typing && !deleting)) {
            drafts.delete(input);
            return;
        }

        event.preventDefault();
        const start = continuing ? previous.start : input.selectionStart;
        const oldEnd = continuing ? previous.end : input.selectionEnd;
        const oldKeys = continuing ? previous.keys : '';
        const newKeys = deleting ? oldKeys.slice(0, -1) : oldKeys + event.key;
        const hangul = compose(newKeys);
        const end = start + hangul.length;
        const value = input.value.slice(0, start) + hangul + input.value.slice(oldEnd);
        setValue.call(input, value);
        input.setSelectionRange(end, end);
        if (newKeys) drafts.set(input, { start, end, keys: newKeys, value });
        else drafts.delete(input);
        input.dispatchEvent(new Event('input', { bubbles: true }));
    }, true);
})();
