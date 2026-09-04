// animations/character.js
// Controls the stick-figure character: center / point left / point right.
const Character = {
  el: null,

  init(el) {
    this.el = el;
  },

  center() {
    this.el.classList.remove("char--left", "char--right");
  },

  pointLeft() {
    this.el.classList.remove("char--right");
    this.el.classList.add("char--left");
  },

  pointRight() {
    this.el.classList.remove("char--left");
    this.el.classList.add("char--right");
  },
};