const feed = document.querySelector('#feed');

// A post keeps its own handwriting from visit to visit. New posts get new gestures.
function randomFor(seed) {
  let state = 2166136261;
  for (const char of seed) state = Math.imul(state ^ char.charCodeAt(0), 16777619);
  return () => {
    state += 0x6D2B79F5;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value ^= value + Math.imul(value ^ (value >>> 7), 61 | value);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function renderPost(post) {
  const random = randomFor(post.id);
  const between = (min, max) => min + random() * (max - min);
  const article = document.createElement('article');
  article.className = 'post';
  article.id = post.id;
  const traits = {
    '--indent': `${between(0, 13).toFixed(2)}%`,
    '--breath': `${between(46, 116).toFixed(1)}px`,
    '--size': `${between(23, 32).toFixed(1)}px`,
    '--turn': `${between(-1.8, 1.8).toFixed(2)}deg`,
    '--answer-turn': `${between(-2.3, 2.3).toFixed(2)}deg`,
    '--diagram-turn': `${between(-0.6, 0.6).toFixed(2)}deg`,
    '--answer-indent': `${between(0, 34).toFixed(1)}px`,
    '--answer-size': between(0.88, 1.15).toFixed(2),
    '--word-gap': `${between(-1, 7).toFixed(1)}px`,
    '--tracking': `${between(-0.3, 1.1).toFixed(2)}px`,
    '--ink': between(0.78, 1).toFixed(2),
    '--before-diagram': `${between(13, 29).toFixed(1)}px`,
    '--after-diagram': `${between(15, 33).toFixed(1)}px`,
    '--date-indent': `${between(0, 40).toFixed(1)}px`,
    '--date-turn': `${between(-2, 2).toFixed(2)}deg`,
  };
  for (const [property, value] of Object.entries(traits)) article.style.setProperty(property, value);

  const text = document.createElement('pre');
  text.className = 'equation';
  const lines = post.text.split('\n');
  // These are real Unicode text nodes, not drawings, duplicated text, or clipboard replacements.
  // Newlines and spaces are preserved exactly; visual spacing lives entirely in CSS.
  if (lines.length >= 3) {
    const title = document.createElement('span');
    title.className = 'word-line subject';
    title.textContent = lines[0];
    const circuit = document.createElement('span');
    circuit.className = 'circuit';
    circuit.textContent = lines.slice(1, -1).join('\n');
    const answer = document.createElement('span');
    answer.className = 'word-line answer';
    answer.textContent = lines[lines.length - 1];
    text.append(title, '\n', circuit, '\n', answer);
  } else {
    text.textContent = post.text;
  }

  const time = document.createElement('time');
  time.dateTime = post.posted_at.replace(' ', 'T');
  time.textContent = post.posted_at.slice(0, 16).replace('T', ' ');
  article.append(text, time);
  return article;
}

fetch('./posts.json', { cache: 'no-store' })
  .then((response) => {
    if (!response.ok) throw new Error(`feed unavailable (${response.status})`);
    return response.json();
  })
  .then(({ posts }) => {
    const fragment = document.createDocumentFragment();
    posts.forEach((post) => fragment.append(renderPost(post)));
    feed.replaceChildren(fragment);
  })
  .catch(() => {
    const post = document.createElement('article');
    post.className = 'post';
    const text = document.createElement('pre');
    text.textContent = 'THE FEED WILL RETURN.';
    post.append(text);
    feed.replaceChildren(post);
  });
