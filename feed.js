const feed = document.querySelector('#feed');

function renderPost(post) {
  const article = document.createElement('article');
  article.className = 'post';
  article.id = post.id;

  const text = document.createElement('pre');
  text.textContent = post.text;

  const time = document.createElement('time');
  time.dateTime = post.posted_at;
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
