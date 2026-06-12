/* Generated file. Source: js/src/dashboard.ts. Do not edit directly. */

"use strict";
(() => {
  // node_modules/gridstack/dist/utils.js
  function obsolete(self, f, oldName, newName, rev) {
    const wrapper = (...args) => {
      console.warn("gridstack.js: Function `" + oldName + "` is deprecated in " + rev + " and has been replaced with `" + newName + "`. It will be **removed** in a future release");
      return f.apply(self, args);
    };
    wrapper.prototype = f.prototype;
    return wrapper;
  }
  var Utils = class _Utils {
    /** convert a potential selector into actual list of html elements. optional root which defaults to document (for shadow dom) */
    static getElements(els, root = document) {
      if (typeof els === "string") {
        const doc = "getElementById" in root ? root : void 0;
        if (doc && !isNaN(+els[0])) {
          const el = doc.getElementById(els);
          return el ? [el] : [];
        }
        let list = root.querySelectorAll(els);
        if (!list.length && els[0] !== "." && els[0] !== "#") {
          list = root.querySelectorAll("." + els);
          if (!list.length) {
            list = root.querySelectorAll("#" + els);
          }
        }
        return Array.from(list);
      }
      return [els];
    }
    /** convert a potential selector into actual single element. optional root which defaults to document (for shadow dom) */
    static getElement(els, root = document) {
      if (typeof els === "string") {
        const doc = "getElementById" in root ? root : void 0;
        if (!els.length)
          return null;
        if (doc && els[0] === "#") {
          return doc.getElementById(els.substring(1));
        }
        if (els[0] === "#" || els[0] === "." || els[0] === "[") {
          return root.querySelector(els);
        }
        if (doc && !isNaN(+els[0])) {
          return doc.getElementById(els);
        }
        let el = root.querySelector(els);
        if (doc && !el) {
          el = doc.getElementById(els);
        }
        if (!el) {
          el = root.querySelector("." + els);
        }
        return el;
      }
      return els;
    }
    /** true if widget (or grid) makes this item lazyLoad */
    static lazyLoad(n) {
      return n.lazyLoad || n.grid?.opts?.lazyLoad && n.lazyLoad !== false;
    }
    /** create a div with the given classes */
    static createDiv(classes, parent) {
      const el = document.createElement("div");
      classes.forEach((c) => {
        if (c)
          el.classList.add(c);
      });
      parent?.appendChild(el);
      return el;
    }
    /** true if we should resize to content. strict=true when only 'sizeToContent:true' and not a number which lets user adjust */
    static shouldSizeToContent(n, strict = false) {
      return n?.grid && (strict ? n.sizeToContent === true || n.grid.opts.sizeToContent === true && n.sizeToContent === void 0 : !!n.sizeToContent || n.grid.opts.sizeToContent && n.sizeToContent !== false);
    }
    /** returns true if a and b overlap */
    static isIntercepted(a, b) {
      return !(a.y >= b.y + b.h || a.y + a.h <= b.y || a.x + a.w <= b.x || a.x >= b.x + b.w);
    }
    /** returns true if a and b touch edges or corners */
    static isTouching(a, b) {
      return _Utils.isIntercepted(a, { x: b.x - 0.5, y: b.y - 0.5, w: b.w + 1, h: b.h + 1 });
    }
    /** returns the area a and b overlap */
    static areaIntercept(a, b) {
      const x0 = a.x > b.x ? a.x : b.x;
      const x1 = a.x + a.w < b.x + b.w ? a.x + a.w : b.x + b.w;
      if (x1 <= x0)
        return 0;
      const y0 = a.y > b.y ? a.y : b.y;
      const y1 = a.y + a.h < b.y + b.h ? a.y + a.h : b.y + b.h;
      if (y1 <= y0)
        return 0;
      return (x1 - x0) * (y1 - y0);
    }
    /** returns the area */
    static area(a) {
      return a.w * a.h;
    }
    /**
     * Sorts array of nodes
     * @param nodes array to sort
     * @param dir 1 for ascending, -1 for descending (optional)
     **/
    static sort(nodes, dir = 1) {
      const und = 1e4;
      return nodes.sort((a, b) => {
        const diffY = dir * ((a.y ?? und) - (b.y ?? und));
        if (diffY === 0)
          return dir * ((a.x ?? und) - (b.x ?? und));
        return diffY;
      });
    }
    /** find an item by id */
    static find(nodes, id) {
      return id ? nodes.find((n) => n.id === id) : void 0;
    }
    /**
     * creates a style sheet with style id under given parent
     * @param id will set the 'gs-style-id' attribute to that id
     * @param parent to insert the stylesheet as first child,
     * if none supplied it will be appended to the document head instead.
     */
    static createStylesheet(id, parent, options) {
      const style = document.createElement("style");
      const nonce = options?.nonce;
      if (nonce)
        style.nonce = nonce;
      style.setAttribute("type", "text/css");
      style.setAttribute("gs-style-id", id);
      if (style.styleSheet) {
        style.styleSheet.cssText = "";
      } else {
        style.appendChild(document.createTextNode(""));
      }
      if (!parent) {
        parent = document.getElementsByTagName("head")[0];
        parent.appendChild(style);
      } else {
        parent.insertBefore(style, parent.firstChild);
      }
      return style;
    }
    /** removed the given stylesheet id */
    static removeStylesheet(id, parent) {
      const target = parent || document;
      const el = target.querySelector("STYLE[gs-style-id=" + id + "]");
      if (el && el.parentNode)
        el.remove();
    }
    /** inserts a CSS rule */
    static addCSSRule(sheet, selector, rules) {
      sheet.textContent += `${selector} { ${rules} } `;
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    static toBool(v) {
      if (typeof v === "boolean") {
        return v;
      }
      if (typeof v === "string") {
        v = v.toLowerCase();
        return !(v === "" || v === "no" || v === "false" || v === "0");
      }
      return Boolean(v);
    }
    static toNumber(value) {
      return value === null || value.length === 0 ? void 0 : Number(value);
    }
    static parseHeight(val) {
      let h;
      let unit = "px";
      if (typeof val === "string") {
        if (val === "auto" || val === "")
          h = 0;
        else {
          const match = val.match(/^(-[0-9]+\.[0-9]+|[0-9]*\.[0-9]+|-[0-9]+|[0-9]+)(px|em|rem|vh|vw|%|cm|mm)?$/);
          if (!match) {
            throw new Error(`Invalid height val = ${val}`);
          }
          unit = match[2] || "px";
          h = parseFloat(match[1]);
        }
      } else {
        h = val;
      }
      return { h, unit };
    }
    /** copies unset fields in target to use the given default sources values */
    // eslint-disable-next-line
    static defaults(target, ...sources) {
      sources.forEach((source) => {
        for (const key in source) {
          if (!source.hasOwnProperty(key))
            return;
          if (target[key] === null || target[key] === void 0) {
            target[key] = source[key];
          } else if (typeof source[key] === "object" && typeof target[key] === "object") {
            this.defaults(target[key], source[key]);
          }
        }
      });
      return target;
    }
    /** given 2 objects return true if they have the same values. Checks for Object {} having same fields and values (just 1 level down) */
    static same(a, b) {
      if (typeof a !== "object")
        return a == b;
      if (typeof a !== typeof b)
        return false;
      if (Object.keys(a).length !== Object.keys(b).length)
        return false;
      for (const key in a) {
        if (a[key] !== b[key])
          return false;
      }
      return true;
    }
    /** copies over b size & position (GridStackPosition), and optionally min/max as well */
    static copyPos(a, b, doMinMax = false) {
      if (b.x !== void 0)
        a.x = b.x;
      if (b.y !== void 0)
        a.y = b.y;
      if (b.w !== void 0)
        a.w = b.w;
      if (b.h !== void 0)
        a.h = b.h;
      if (doMinMax) {
        if (b.minW)
          a.minW = b.minW;
        if (b.minH)
          a.minH = b.minH;
        if (b.maxW)
          a.maxW = b.maxW;
        if (b.maxH)
          a.maxH = b.maxH;
      }
      return a;
    }
    /** true if a and b has same size & position */
    static samePos(a, b) {
      return a && b && a.x === b.x && a.y === b.y && (a.w || 1) === (b.w || 1) && (a.h || 1) === (b.h || 1);
    }
    /** given a node, makes sure it's min/max are valid */
    static sanitizeMinMax(node) {
      if (!node.minW) {
        delete node.minW;
      }
      if (!node.minH) {
        delete node.minH;
      }
      if (!node.maxW) {
        delete node.maxW;
      }
      if (!node.maxH) {
        delete node.maxH;
      }
    }
    /** removes field from the first object if same as the second objects (like diffing) and internal '_' for saving */
    static removeInternalAndSame(a, b) {
      if (typeof a !== "object" || typeof b !== "object")
        return;
      for (let key in a) {
        const aVal = a[key];
        const bVal = b[key];
        if (key[0] === "_" || aVal === bVal) {
          delete a[key];
        } else if (aVal && typeof aVal === "object" && bVal !== void 0) {
          _Utils.removeInternalAndSame(aVal, bVal);
          if (!Object.keys(aVal).length) {
            delete a[key];
          }
        }
      }
    }
    /** removes internal fields '_' and default values for saving */
    static removeInternalForSave(n, removeEl = true) {
      for (let key in n) {
        if (key[0] === "_" || n[key] === null || n[key] === void 0)
          delete n[key];
      }
      delete n.grid;
      if (removeEl)
        delete n.el;
      if (!n.autoPosition)
        delete n.autoPosition;
      if (!n.noResize)
        delete n.noResize;
      if (!n.noMove)
        delete n.noMove;
      if (!n.locked)
        delete n.locked;
      if (n.w === 1 || n.w === n.minW)
        delete n.w;
      if (n.h === 1 || n.h === n.minH)
        delete n.h;
    }
    /** return the closest parent (or itself) matching the given class */
    // static closestUpByClass(el: HTMLElement, name: string): HTMLElement {
    //   while (el) {
    //     if (el.classList.contains(name)) return el;
    //     el = el.parentElement
    //   }
    //   return null;
    // }
    /** delay calling the given function for given delay, preventing new calls from happening while waiting */
    static throttle(func, delay) {
      let isWaiting = false;
      return (...args) => {
        if (!isWaiting) {
          isWaiting = true;
          setTimeout(() => {
            func(...args);
            isWaiting = false;
          }, delay);
        }
      };
    }
    static removePositioningStyles(el) {
      const style = el.style;
      if (style.position) {
        style.removeProperty("position");
      }
      if (style.left) {
        style.removeProperty("left");
      }
      if (style.top) {
        style.removeProperty("top");
      }
      if (style.width) {
        style.removeProperty("width");
      }
      if (style.height) {
        style.removeProperty("height");
      }
    }
    /** @internal returns the passed element if scrollable, else the closest parent that will, up to the entire document scrolling element */
    static getScrollElement(el) {
      if (!el)
        return document.scrollingElement || document.documentElement;
      const style = getComputedStyle(el);
      const overflowRegex = /(auto|scroll)/;
      if (overflowRegex.test(style.overflow + style.overflowY)) {
        return el;
      } else {
        return this.getScrollElement(el.parentElement);
      }
    }
    /** @internal */
    static updateScrollPosition(el, position, distance) {
      const rect = el.getBoundingClientRect();
      const innerHeightOrClientHeight = window.innerHeight || document.documentElement.clientHeight;
      if (rect.top < 0 || rect.bottom > innerHeightOrClientHeight) {
        const offsetDiffDown = rect.bottom - innerHeightOrClientHeight;
        const offsetDiffUp = rect.top;
        const scrollEl = this.getScrollElement(el);
        if (scrollEl !== null) {
          const prevScroll = scrollEl.scrollTop;
          if (rect.top < 0 && distance < 0) {
            if (el.offsetHeight > innerHeightOrClientHeight) {
              scrollEl.scrollTop += distance;
            } else {
              scrollEl.scrollTop += Math.abs(offsetDiffUp) > Math.abs(distance) ? distance : offsetDiffUp;
            }
          } else if (distance > 0) {
            if (el.offsetHeight > innerHeightOrClientHeight) {
              scrollEl.scrollTop += distance;
            } else {
              scrollEl.scrollTop += offsetDiffDown > distance ? distance : offsetDiffDown;
            }
          }
          position.top += scrollEl.scrollTop - prevScroll;
        }
      }
    }
    /**
     * @internal Function used to scroll the page.
     *
     * @param event `MouseEvent` that triggers the resize
     * @param el `HTMLElement` that's being resized
     * @param distance Distance from the V edges to start scrolling
     */
    static updateScrollResize(event, el, distance) {
      const scrollEl = this.getScrollElement(el);
      const height = scrollEl.clientHeight;
      const offsetTop = scrollEl === this.getScrollElement() ? 0 : scrollEl.getBoundingClientRect().top;
      const pointerPosY = event.clientY - offsetTop;
      const top = pointerPosY < distance;
      const bottom = pointerPosY > height - distance;
      if (top) {
        scrollEl.scrollBy({ behavior: "smooth", top: pointerPosY - distance });
      } else if (bottom) {
        scrollEl.scrollBy({ behavior: "smooth", top: distance - (height - pointerPosY) });
      }
    }
    /** single level clone, returning a new object with same top fields. This will share sub objects and arrays */
    static clone(obj) {
      if (obj === null || obj === void 0 || typeof obj !== "object") {
        return obj;
      }
      if (obj instanceof Array) {
        return [...obj];
      }
      return { ...obj };
    }
    /**
     * Recursive clone version that returns a full copy, checking for nested objects and arrays ONLY.
     * Note: this will use as-is any key starting with double __ (and not copy inside) some lib have circular dependencies.
     */
    static cloneDeep(obj) {
      const skipFields = ["parentGrid", "el", "grid", "subGrid", "engine"];
      const ret = _Utils.clone(obj);
      for (const key in ret) {
        if (ret.hasOwnProperty(key) && typeof ret[key] === "object" && key.substring(0, 2) !== "__" && !skipFields.find((k) => k === key)) {
          ret[key] = _Utils.cloneDeep(obj[key]);
        }
      }
      return ret;
    }
    /** deep clone the given HTML node, removing teh unique id field */
    static cloneNode(el) {
      const node = el.cloneNode(true);
      node.removeAttribute("id");
      return node;
    }
    static appendTo(el, parent) {
      let parentNode;
      if (typeof parent === "string") {
        parentNode = _Utils.getElement(parent);
      } else {
        parentNode = parent;
      }
      if (parentNode) {
        parentNode.appendChild(el);
      }
    }
    // public static setPositionRelative(el: HTMLElement): void {
    //   if (!(/^(?:r|a|f)/).test(getComputedStyle(el).position)) {
    //     el.style.position = "relative";
    //   }
    // }
    static addElStyles(el, styles) {
      if (styles instanceof Object) {
        for (const s in styles) {
          if (styles.hasOwnProperty(s)) {
            if (Array.isArray(styles[s])) {
              styles[s].forEach((val) => {
                el.style[s] = val;
              });
            } else {
              el.style[s] = styles[s];
            }
          }
        }
      }
    }
    static initEvent(e, info) {
      const evt = { type: info.type };
      const obj = {
        button: 0,
        which: 0,
        buttons: 1,
        bubbles: true,
        cancelable: true,
        target: info.target ? info.target : e.target
      };
      ["altKey", "ctrlKey", "metaKey", "shiftKey"].forEach((p) => evt[p] = e[p]);
      ["pageX", "pageY", "clientX", "clientY", "screenX", "screenY"].forEach((p) => evt[p] = e[p]);
      return { ...evt, ...obj };
    }
    /** copies the MouseEvent (or convert Touch) properties and sends it as another event to the given target */
    static simulateMouseEvent(e, simulatedType, target) {
      const me = e;
      const simulatedEvent = new MouseEvent(simulatedType, {
        bubbles: true,
        composed: true,
        cancelable: true,
        view: window,
        detail: 1,
        screenX: e.screenX,
        screenY: e.screenY,
        clientX: e.clientX,
        clientY: e.clientY,
        ctrlKey: me.ctrlKey ?? false,
        altKey: me.altKey ?? false,
        shiftKey: me.shiftKey ?? false,
        metaKey: me.metaKey ?? false,
        button: 0,
        relatedTarget: e.target
      });
      (target || e.target).dispatchEvent(simulatedEvent);
    }
    /**
     * defines an element that is used to get the offset and scale from grid transforms
     * returns the scale and offsets from said element
    */
    static getValuesFromTransformedElement(parent) {
      const transformReference = document.createElement("div");
      _Utils.addElStyles(transformReference, {
        opacity: "0",
        position: "fixed",
        top: "0px",
        left: "0px",
        width: "1px",
        height: "1px",
        zIndex: "-999999"
      });
      parent.appendChild(transformReference);
      const transformValues = transformReference.getBoundingClientRect();
      parent.removeChild(transformReference);
      transformReference.remove();
      return {
        xScale: 1 / transformValues.width,
        yScale: 1 / transformValues.height,
        xOffset: transformValues.left,
        yOffset: transformValues.top
      };
    }
    /** swap the given object 2 field values */
    static swap(o, a, b) {
      if (!o)
        return;
      const tmp = o[a];
      o[a] = o[b];
      o[b] = tmp;
    }
    /** returns true if event is inside the given element rectangle */
    // Note: Safari Mac has null event.relatedTarget which causes #1684 so check if DragEvent is inside the coordinates instead
    //    this.el.contains(event.relatedTarget as HTMLElement)
    // public static inside(e: MouseEvent, el: HTMLElement): boolean {
    //   // srcElement, toElement, target: all set to placeholder when leaving simple grid, so we can't use that (Chrome)
    //   const target: HTMLElement = e.relatedTarget || (e as any).fromElement;
    //   if (!target) {
    //     const { bottom, left, right, top } = el.getBoundingClientRect();
    //     return (e.x < right && e.x > left && e.y < bottom && e.y > top);
    //   }
    //   return el.contains(target);
    // }
    /** true if the item can be rotated (checking for prop, not space available) */
    static canBeRotated(n) {
      return !(!n || n.w === n.h || n.locked || n.noResize || n.grid?.opts.disableResize || n.minW && n.minW === n.maxW || n.minH && n.minH === n.maxH);
    }
  };

  // node_modules/gridstack/dist/gridstack-engine.js
  var GridStackEngine = class _GridStackEngine {
    constructor(opts = {}) {
      this.addedNodes = [];
      this.removedNodes = [];
      this.defaultColumn = 12;
      this.column = opts.column || this.defaultColumn;
      if (this.column > this.defaultColumn)
        this.defaultColumn = this.column;
      this.maxRow = opts.maxRow;
      this._float = opts.float;
      this.nodes = opts.nodes || [];
      this.onChange = opts.onChange;
    }
    batchUpdate(flag = true, doPack = true) {
      if (!!this.batchMode === flag)
        return this;
      this.batchMode = flag;
      if (flag) {
        this._prevFloat = this._float;
        this._float = true;
        this.cleanNodes();
        this.saveInitial();
      } else {
        this._float = this._prevFloat;
        delete this._prevFloat;
        if (doPack)
          this._packNodes();
        this._notify();
      }
      return this;
    }
    // use entire row for hitting area (will use bottom reverse sorted first) if we not actively moving DOWN and didn't already skip
    _useEntireRowArea(node, nn) {
      return (!this.float || this.batchMode && !this._prevFloat) && !this._hasLocked && (!node._moving || node._skipDown || nn.y <= node.y);
    }
    /** @internal fix collision on given 'node', going to given new location 'nn', with optional 'collide' node already found.
     * return true if we moved. */
    _fixCollisions(node, nn = node, collide, opt = {}) {
      this.sortNodes(-1);
      collide = collide || this.collide(node, nn);
      if (!collide)
        return false;
      if (node._moving && !opt.nested && !this.float) {
        if (this.swap(node, collide))
          return true;
      }
      let area = nn;
      if (!this._loading && this._useEntireRowArea(node, nn)) {
        area = { x: 0, w: this.column, y: nn.y, h: nn.h };
        collide = this.collide(node, area, opt.skip);
      }
      let didMove = false;
      const newOpt = { nested: true, pack: false };
      let counter = 0;
      while (collide = collide || this.collide(node, area, opt.skip)) {
        if (counter++ > this.nodes.length * 2) {
          throw new Error("Infinite collide check");
        }
        let moved;
        if (collide.locked || this._loading || node._moving && !node._skipDown && nn.y > node.y && !this.float && // can take space we had, or before where we're going
        (!this.collide(collide, { ...collide, y: node.y }, node) || !this.collide(collide, { ...collide, y: nn.y - collide.h }, node))) {
          node._skipDown = node._skipDown || nn.y > node.y;
          const newNN = { ...nn, y: collide.y + collide.h, ...newOpt };
          moved = this._loading && Utils.samePos(node, newNN) ? true : this.moveNode(node, newNN);
          if ((collide.locked || this._loading) && moved) {
            Utils.copyPos(nn, node);
          } else if (!collide.locked && moved && opt.pack) {
            this._packNodes();
            nn.y = collide.y + collide.h;
            Utils.copyPos(node, nn);
          }
          didMove = didMove || moved;
        } else {
          moved = this.moveNode(collide, { ...collide, y: nn.y + nn.h, skip: node, ...newOpt });
        }
        if (!moved)
          return didMove;
        collide = void 0;
      }
      return didMove;
    }
    /** return the nodes that intercept the given node. Optionally a different area can be used, as well as a second node to skip */
    collide(skip, area = skip, skip2) {
      const skipId = skip._id;
      const skip2Id = skip2?._id;
      return this.nodes.find((n) => n._id !== skipId && n._id !== skip2Id && Utils.isIntercepted(n, area));
    }
    collideAll(skip, area = skip, skip2) {
      const skipId = skip._id;
      const skip2Id = skip2?._id;
      return this.nodes.filter((n) => n._id !== skipId && n._id !== skip2Id && Utils.isIntercepted(n, area));
    }
    /** does a pixel coverage collision based on where we started, returning the node that has the most coverage that is >50% mid line */
    directionCollideCoverage(node, o, collides) {
      if (!o.rect || !node._rect)
        return;
      const r0 = node._rect;
      const r = { ...o.rect };
      if (r.y > r0.y) {
        r.h += r.y - r0.y;
        r.y = r0.y;
      } else {
        r.h += r0.y - r.y;
      }
      if (r.x > r0.x) {
        r.w += r.x - r0.x;
        r.x = r0.x;
      } else {
        r.w += r0.x - r.x;
      }
      let collide;
      let overMax = 0.5;
      for (let n of collides) {
        if (n.locked || !n._rect) {
          break;
        }
        const r2 = n._rect;
        let yOver = Number.MAX_VALUE, xOver = Number.MAX_VALUE;
        if (r0.y < r2.y) {
          yOver = (r.y + r.h - r2.y) / r2.h;
        } else if (r0.y + r0.h > r2.y + r2.h) {
          yOver = (r2.y + r2.h - r.y) / r2.h;
        }
        if (r0.x < r2.x) {
          xOver = (r.x + r.w - r2.x) / r2.w;
        } else if (r0.x + r0.w > r2.x + r2.w) {
          xOver = (r2.x + r2.w - r.x) / r2.w;
        }
        const over = Math.min(xOver, yOver);
        if (over > overMax) {
          overMax = over;
          collide = n;
        }
      }
      o.collide = collide;
      return collide;
    }
    /** does a pixel coverage returning the node that has the most coverage by area */
    /*
    protected collideCoverage(r: GridStackPosition, collides: GridStackNode[]): {collide: GridStackNode, over: number} {
      const collide: GridStackNode;
      const overMax = 0;
      collides.forEach(n => {
        if (n.locked || !n._rect) return;
        const over = Utils.areaIntercept(r, n._rect);
        if (over > overMax) {
          overMax = over;
          collide = n;
        }
      });
      return {collide, over: overMax};
    }
    */
    /** called to cache the nodes pixel rectangles used for collision detection during drag */
    cacheRects(w, h, top, right, bottom, left) {
      this.nodes.forEach((n) => n._rect = {
        y: n.y * h + top,
        x: n.x * w + left,
        w: n.w * w - left - right,
        h: n.h * h - top - bottom
      });
      return this;
    }
    /** called to possibly swap between 2 nodes (same size or column, not locked, touching), returning true if successful */
    swap(a, b) {
      if (!b || b.locked || !a || a.locked)
        return false;
      function _doSwap() {
        const x = b.x, y = b.y;
        b.x = a.x;
        b.y = a.y;
        if (a.h != b.h) {
          a.x = x;
          a.y = b.y + b.h;
        } else if (a.w != b.w) {
          a.x = b.x + b.w;
          a.y = y;
        } else {
          a.x = x;
          a.y = y;
        }
        a._dirty = b._dirty = true;
        return true;
      }
      let touching;
      if (a.w === b.w && a.h === b.h && (a.x === b.x || a.y === b.y) && (touching = Utils.isTouching(a, b)))
        return _doSwap();
      if (touching === false)
        return;
      if (a.w === b.w && a.x === b.x && (touching || (touching = Utils.isTouching(a, b)))) {
        if (b.y < a.y) {
          const t = a;
          a = b;
          b = t;
        }
        return _doSwap();
      }
      if (touching === false)
        return;
      if (a.h === b.h && a.y === b.y && (touching || (touching = Utils.isTouching(a, b)))) {
        if (b.x < a.x) {
          const t = a;
          a = b;
          b = t;
        }
        return _doSwap();
      }
      return false;
    }
    isAreaEmpty(x, y, w, h) {
      const nn = { x: x || 0, y: y || 0, w: w || 1, h: h || 1 };
      return !this.collide(nn);
    }
    /** re-layout grid items to reclaim any empty space - optionally keeping the sort order exactly the same ('list' mode) vs truly finding an empty spaces */
    compact(layout = "compact", doSort = true) {
      if (this.nodes.length === 0)
        return this;
      if (doSort)
        this.sortNodes();
      const wasBatch = this.batchMode;
      if (!wasBatch)
        this.batchUpdate();
      const wasColumnResize = this._inColumnResize;
      if (!wasColumnResize)
        this._inColumnResize = true;
      const copyNodes = this.nodes;
      this.nodes = [];
      copyNodes.forEach((n, index, list) => {
        let after;
        if (!n.locked) {
          n.autoPosition = true;
          if (layout === "list" && index)
            after = list[index - 1];
        }
        this.addNode(n, false, after);
      });
      if (!wasColumnResize)
        delete this._inColumnResize;
      if (!wasBatch)
        this.batchUpdate(false);
      return this;
    }
    /** enable/disable floating widgets (default: `false`) See [example](http://gridstackjs.com/demo/float.html) */
    set float(val) {
      if (this._float === val)
        return;
      this._float = val || false;
      if (!val) {
        this._packNodes()._notify();
      }
    }
    /** float getter method */
    get float() {
      return this._float || false;
    }
    /** sort the nodes array from first to last, or reverse. Called during collision/placement to force an order */
    sortNodes(dir = 1) {
      this.nodes = Utils.sort(this.nodes, dir);
      return this;
    }
    /** @internal called to top gravity pack the items back OR revert back to original Y positions when floating */
    _packNodes() {
      if (this.batchMode) {
        return this;
      }
      this.sortNodes();
      if (this.float) {
        this.nodes.forEach((n) => {
          if (n._updating || n._orig === void 0 || n.y === n._orig.y)
            return;
          let newY = n.y;
          while (newY > n._orig.y) {
            --newY;
            const collide = this.collide(n, { x: n.x, y: newY, w: n.w, h: n.h });
            if (!collide) {
              n._dirty = true;
              n.y = newY;
            }
          }
        });
      } else {
        this.nodes.forEach((n, i) => {
          if (n.locked)
            return;
          while (n.y > 0) {
            const newY = i === 0 ? 0 : n.y - 1;
            const canBeMoved = i === 0 || !this.collide(n, { x: n.x, y: newY, w: n.w, h: n.h });
            if (!canBeMoved)
              break;
            n._dirty = n.y !== newY;
            n.y = newY;
          }
        });
      }
      return this;
    }
    /**
     * given a random node, makes sure it's coordinates/values are valid in the current grid
     * @param node to adjust
     * @param resizing if out of bound, resize down or move into the grid to fit ?
     */
    prepareNode(node, resizing) {
      node._id = node._id ?? _GridStackEngine._idSeq++;
      const id = node.id;
      if (id) {
        let count = 1;
        while (this.nodes.find((n) => n.id === node.id && n !== node)) {
          node.id = id + "_" + count++;
        }
      }
      if (node.x === void 0 || node.y === void 0 || node.x === null || node.y === null) {
        node.autoPosition = true;
      }
      const defaults = { x: 0, y: 0, w: 1, h: 1 };
      Utils.defaults(node, defaults);
      if (!node.autoPosition) {
        delete node.autoPosition;
      }
      if (!node.noResize) {
        delete node.noResize;
      }
      if (!node.noMove) {
        delete node.noMove;
      }
      Utils.sanitizeMinMax(node);
      if (typeof node.x == "string") {
        node.x = Number(node.x);
      }
      if (typeof node.y == "string") {
        node.y = Number(node.y);
      }
      if (typeof node.w == "string") {
        node.w = Number(node.w);
      }
      if (typeof node.h == "string") {
        node.h = Number(node.h);
      }
      if (isNaN(node.x)) {
        node.x = defaults.x;
        node.autoPosition = true;
      }
      if (isNaN(node.y)) {
        node.y = defaults.y;
        node.autoPosition = true;
      }
      if (isNaN(node.w)) {
        node.w = defaults.w;
      }
      if (isNaN(node.h)) {
        node.h = defaults.h;
      }
      this.nodeBoundFix(node, resizing);
      return node;
    }
    /** part2 of preparing a node to fit inside our grid - checks for x,y,w from grid dimensions */
    nodeBoundFix(node, resizing) {
      const before = node._orig || Utils.copyPos({}, node);
      if (node.maxW) {
        node.w = Math.min(node.w || 1, node.maxW);
      }
      if (node.maxH) {
        node.h = Math.min(node.h || 1, node.maxH);
      }
      if (node.minW) {
        node.w = Math.max(node.w || 1, node.minW);
      }
      if (node.minH) {
        node.h = Math.max(node.h || 1, node.minH);
      }
      const saveOrig = (node.x || 0) + (node.w || 1) > this.column;
      if (saveOrig && this.column < this.defaultColumn && !this._inColumnResize && !this.skipCacheUpdate && node._id && this.findCacheLayout(node, this.defaultColumn) === -1) {
        const copy = { ...node };
        if (copy.autoPosition || copy.x === void 0) {
          delete copy.x;
          delete copy.y;
        } else
          copy.x = Math.min(this.defaultColumn - 1, copy.x);
        copy.w = Math.min(this.defaultColumn, copy.w || 1);
        this.cacheOneLayout(copy, this.defaultColumn);
      }
      if (node.w > this.column) {
        node.w = this.column;
      } else if (node.w < 1) {
        node.w = 1;
      }
      if (this.maxRow && node.h > this.maxRow) {
        node.h = this.maxRow;
      } else if (node.h < 1) {
        node.h = 1;
      }
      if (node.x < 0) {
        node.x = 0;
      }
      if (node.y < 0) {
        node.y = 0;
      }
      if (node.x + node.w > this.column) {
        if (resizing) {
          node.w = this.column - node.x;
        } else {
          node.x = this.column - node.w;
        }
      }
      if (this.maxRow && node.y + node.h > this.maxRow) {
        if (resizing) {
          node.h = this.maxRow - node.y;
        } else {
          node.y = this.maxRow - node.h;
        }
      }
      if (!Utils.samePos(node, before)) {
        node._dirty = true;
      }
      return this;
    }
    /** returns a list of modified nodes from their original values */
    getDirtyNodes(verify) {
      if (verify) {
        return this.nodes.filter((n) => n._dirty && !Utils.samePos(n, n._orig));
      }
      return this.nodes.filter((n) => n._dirty);
    }
    /** @internal call this to call onChange callback with dirty nodes so DOM can be updated */
    _notify(removedNodes) {
      if (this.batchMode || !this.onChange)
        return this;
      const dirtyNodes = (removedNodes || []).concat(this.getDirtyNodes());
      this.onChange(dirtyNodes);
      return this;
    }
    /** @internal remove dirty and last tried info */
    cleanNodes() {
      if (this.batchMode)
        return this;
      this.nodes.forEach((n) => {
        delete n._dirty;
        delete n._lastTried;
      });
      return this;
    }
    /** @internal called to save initial position/size to track real dirty state.
     * Note: should be called right after we call change event (so next API is can detect changes)
     * as well as right before we start move/resize/enter (so we can restore items to prev values) */
    saveInitial() {
      this.nodes.forEach((n) => {
        n._orig = Utils.copyPos({}, n);
        delete n._dirty;
      });
      this._hasLocked = this.nodes.some((n) => n.locked);
      return this;
    }
    /** @internal restore all the nodes back to initial values (called when we leave) */
    restoreInitial() {
      this.nodes.forEach((n) => {
        if (!n._orig || Utils.samePos(n, n._orig))
          return;
        Utils.copyPos(n, n._orig);
        n._dirty = true;
      });
      this._notify();
      return this;
    }
    /** find the first available empty spot for the given node width/height, updating the x,y attributes. return true if found.
     * optionally you can pass your own existing node list and column count, otherwise defaults to that engine data.
     * Optionally pass a widget to start search AFTER, meaning the order will remain the same but possibly have empty slots we skipped
     */
    findEmptyPosition(node, nodeList = this.nodes, column = this.column, after) {
      const start = after ? after.y * column + (after.x + after.w) : 0;
      let found = false;
      for (let i = start; !found; ++i) {
        const x = i % column;
        const y = Math.floor(i / column);
        if (x + node.w > column) {
          continue;
        }
        const box = { x, y, w: node.w, h: node.h };
        if (!nodeList.find((n) => Utils.isIntercepted(box, n))) {
          if (node.x !== x || node.y !== y)
            node._dirty = true;
          node.x = x;
          node.y = y;
          delete node.autoPosition;
          found = true;
        }
      }
      return found;
    }
    /** call to add the given node to our list, fixing collision and re-packing */
    addNode(node, triggerAddEvent = false, after) {
      const dup = this.nodes.find((n) => n._id === node._id);
      if (dup)
        return dup;
      this._inColumnResize ? this.nodeBoundFix(node) : this.prepareNode(node);
      delete node._temporaryRemoved;
      delete node._removeDOM;
      let skipCollision;
      if (node.autoPosition && this.findEmptyPosition(node, this.nodes, this.column, after)) {
        delete node.autoPosition;
        skipCollision = true;
      }
      this.nodes.push(node);
      if (triggerAddEvent) {
        this.addedNodes.push(node);
      }
      if (!skipCollision)
        this._fixCollisions(node);
      if (!this.batchMode) {
        this._packNodes()._notify();
      }
      return node;
    }
    removeNode(node, removeDOM = true, triggerEvent = false) {
      if (!this.nodes.find((n) => n._id === node._id)) {
        return this;
      }
      if (triggerEvent) {
        this.removedNodes.push(node);
      }
      if (removeDOM)
        node._removeDOM = true;
      this.nodes = this.nodes.filter((n) => n._id !== node._id);
      if (!node._isAboutToRemove)
        this._packNodes();
      this._notify([node]);
      return this;
    }
    removeAll(removeDOM = true, triggerEvent = true) {
      delete this._layouts;
      if (!this.nodes.length)
        return this;
      removeDOM && this.nodes.forEach((n) => n._removeDOM = true);
      const removedNodes = this.nodes;
      this.removedNodes = triggerEvent ? removedNodes : [];
      this.nodes = [];
      return this._notify(removedNodes);
    }
    /** checks if item can be moved (layout constrain) vs moveNode(), returning true if was able to move.
     * In more complicated cases (maxRow) it will attempt at moving the item and fixing
     * others in a clone first, then apply those changes if still within specs. */
    moveNodeCheck(node, o) {
      if (!this.changedPosConstrain(node, o))
        return false;
      o.pack = true;
      if (!this.maxRow) {
        return this.moveNode(node, o);
      }
      let clonedNode;
      const clone = new _GridStackEngine({
        column: this.column,
        float: this.float,
        nodes: this.nodes.map((n) => {
          if (n._id === node._id) {
            clonedNode = { ...n };
            return clonedNode;
          }
          return { ...n };
        })
      });
      if (!clonedNode)
        return false;
      const canMove = clone.moveNode(clonedNode, o) && clone.getRow() <= Math.max(this.getRow(), this.maxRow);
      if (!canMove && !o.resizing && o.collide) {
        const collide = o.collide.el.gridstackNode;
        if (this.swap(node, collide)) {
          this._notify();
          return true;
        }
      }
      if (!canMove)
        return false;
      clone.nodes.filter((n) => n._dirty).forEach((c) => {
        const n = this.nodes.find((a) => a._id === c._id);
        if (!n)
          return;
        Utils.copyPos(n, c);
        n._dirty = true;
      });
      this._notify();
      return true;
    }
    /** return true if can fit in grid height constrain only (always true if no maxRow) */
    willItFit(node) {
      delete node._willFitPos;
      if (!this.maxRow)
        return true;
      const clone = new _GridStackEngine({
        column: this.column,
        float: this.float,
        nodes: this.nodes.map((n2) => {
          return { ...n2 };
        })
      });
      const n = { ...node };
      this.cleanupNode(n);
      delete n.el;
      delete n._id;
      delete n.content;
      delete n.grid;
      clone.addNode(n);
      if (clone.getRow() <= this.maxRow) {
        node._willFitPos = Utils.copyPos({}, n);
        return true;
      }
      return false;
    }
    /** true if x,y or w,h are different after clamping to min/max */
    changedPosConstrain(node, p) {
      p.w = p.w || node.w;
      p.h = p.h || node.h;
      if (node.x !== p.x || node.y !== p.y)
        return true;
      if (node.maxW) {
        p.w = Math.min(p.w, node.maxW);
      }
      if (node.maxH) {
        p.h = Math.min(p.h, node.maxH);
      }
      if (node.minW) {
        p.w = Math.max(p.w, node.minW);
      }
      if (node.minH) {
        p.h = Math.max(p.h, node.minH);
      }
      return node.w !== p.w || node.h !== p.h;
    }
    /** return true if the passed in node was actually moved (checks for no-op and locked) */
    moveNode(node, o) {
      if (!node || /*node.locked ||*/
      !o)
        return false;
      let wasUndefinedPack;
      if (o.pack === void 0 && !this.batchMode) {
        wasUndefinedPack = o.pack = true;
      }
      if (typeof o.x !== "number") {
        o.x = node.x;
      }
      if (typeof o.y !== "number") {
        o.y = node.y;
      }
      if (typeof o.w !== "number") {
        o.w = node.w;
      }
      if (typeof o.h !== "number") {
        o.h = node.h;
      }
      const resizing = node.w !== o.w || node.h !== o.h;
      const nn = Utils.copyPos({}, node, true);
      Utils.copyPos(nn, o);
      this.nodeBoundFix(nn, resizing);
      Utils.copyPos(o, nn);
      if (!o.forceCollide && Utils.samePos(node, o))
        return false;
      const prevPos = Utils.copyPos({}, node);
      const collides = this.collideAll(node, nn, o.skip);
      let needToMove = true;
      if (collides.length) {
        const activeDrag = node._moving && !o.nested;
        let collide = activeDrag ? this.directionCollideCoverage(node, o, collides) : collides[0];
        if (activeDrag && collide && node.grid?.opts?.subGridDynamic && !node.grid._isTemp) {
          const over = Utils.areaIntercept(o.rect, collide._rect);
          const a1 = Utils.area(o.rect);
          const a2 = Utils.area(collide._rect);
          const perc = over / (a1 < a2 ? a1 : a2);
          if (perc > 0.8) {
            collide.grid.makeSubGrid(collide.el, void 0, node);
            collide = void 0;
          }
        }
        if (collide) {
          needToMove = !this._fixCollisions(node, nn, collide, o);
        } else {
          needToMove = false;
          if (wasUndefinedPack)
            delete o.pack;
        }
      }
      if (needToMove && !Utils.samePos(node, nn)) {
        node._dirty = true;
        Utils.copyPos(node, nn);
      }
      if (o.pack) {
        this._packNodes()._notify();
      }
      return !Utils.samePos(node, prevPos);
    }
    getRow() {
      return this.nodes.reduce((row, n) => Math.max(row, n.y + n.h), 0);
    }
    beginUpdate(node) {
      if (!node._updating) {
        node._updating = true;
        delete node._skipDown;
        if (!this.batchMode)
          this.saveInitial();
      }
      return this;
    }
    endUpdate() {
      const n = this.nodes.find((n2) => n2._updating);
      if (n) {
        delete n._updating;
        delete n._skipDown;
      }
      return this;
    }
    /** saves a copy of the largest column layout (eg 12 even when rendering oneColumnMode) so we don't loose orig layout,
     * returning a list of widgets for serialization */
    save(saveElement = true, saveCB) {
      const len = this._layouts?.length;
      const layout = len && this.column !== len - 1 ? this._layouts[len - 1] : null;
      const list = [];
      this.sortNodes();
      this.nodes.forEach((n) => {
        const wl = layout?.find((l) => l._id === n._id);
        const w = { ...n, ...wl || {} };
        Utils.removeInternalForSave(w, !saveElement);
        if (saveCB)
          saveCB(n, w);
        list.push(w);
      });
      return list;
    }
    /** @internal called whenever a node is added or moved - updates the cached layouts */
    layoutsNodesChange(nodes) {
      if (!this._layouts || this._inColumnResize)
        return this;
      this._layouts.forEach((layout, column) => {
        if (!layout || column === this.column)
          return this;
        if (column < this.column) {
          this._layouts[column] = void 0;
        } else {
          const ratio = column / this.column;
          nodes.forEach((node) => {
            if (!node._orig)
              return;
            const n = layout.find((l) => l._id === node._id);
            if (!n)
              return;
            if (n.y >= 0 && node.y !== node._orig.y) {
              n.y += node.y - node._orig.y;
            }
            if (node.x !== node._orig.x) {
              n.x = Math.round(node.x * ratio);
            }
            if (node.w !== node._orig.w) {
              n.w = Math.round(node.w * ratio);
            }
          });
        }
      });
      return this;
    }
    /**
     * @internal Called to scale the widget width & position up/down based on the column change.
     * Note we store previous layouts (especially original ones) to make it possible to go
     * from say 12 -> 1 -> 12 and get back to where we were.
     *
     * @param prevColumn previous number of columns
     * @param column  new column number
     * @param layout specify the type of re-layout that will happen (position, size, etc...).
     * Note: items will never be outside of the current column boundaries. default (moveScale). Ignored for 1 column
     */
    columnChanged(prevColumn, column, layout = "moveScale") {
      if (!this.nodes.length || !column || prevColumn === column)
        return this;
      const doCompact = layout === "compact" || layout === "list";
      if (doCompact) {
        this.sortNodes(1);
      }
      if (column < prevColumn)
        this.cacheLayout(this.nodes, prevColumn);
      this.batchUpdate();
      let newNodes = [];
      let nodes = doCompact ? this.nodes : Utils.sort(this.nodes, -1);
      if (column > prevColumn && this._layouts) {
        const cacheNodes = this._layouts[column] || [];
        const lastIndex = this._layouts.length - 1;
        if (!cacheNodes.length && prevColumn !== lastIndex && this._layouts[lastIndex]?.length) {
          prevColumn = lastIndex;
          this._layouts[lastIndex].forEach((cacheNode) => {
            const n = nodes.find((n2) => n2._id === cacheNode._id);
            if (n) {
              if (!doCompact && !cacheNode.autoPosition) {
                n.x = cacheNode.x ?? n.x;
                n.y = cacheNode.y ?? n.y;
              }
              n.w = cacheNode.w ?? n.w;
              if (cacheNode.x == void 0 || cacheNode.y === void 0)
                n.autoPosition = true;
            }
          });
        }
        cacheNodes.forEach((cacheNode) => {
          const j = nodes.findIndex((n) => n._id === cacheNode._id);
          if (j !== -1) {
            const n = nodes[j];
            if (doCompact) {
              n.w = cacheNode.w;
              return;
            }
            if (cacheNode.autoPosition || isNaN(cacheNode.x) || isNaN(cacheNode.y)) {
              this.findEmptyPosition(cacheNode, newNodes);
            }
            if (!cacheNode.autoPosition) {
              n.x = cacheNode.x ?? n.x;
              n.y = cacheNode.y ?? n.y;
              n.w = cacheNode.w ?? n.w;
              newNodes.push(n);
            }
            nodes.splice(j, 1);
          }
        });
      }
      if (doCompact) {
        this.compact(layout, false);
      } else {
        if (nodes.length) {
          if (typeof layout === "function") {
            layout(column, prevColumn, newNodes, nodes);
          } else {
            const ratio = doCompact || layout === "none" ? 1 : column / prevColumn;
            const move = layout === "move" || layout === "moveScale";
            const scale = layout === "scale" || layout === "moveScale";
            nodes.forEach((node) => {
              node.x = column === 1 ? 0 : move ? Math.round(node.x * ratio) : Math.min(node.x, column - 1);
              node.w = column === 1 || prevColumn === 1 ? 1 : scale ? Math.round(node.w * ratio) || 1 : Math.min(node.w, column);
              newNodes.push(node);
            });
            nodes = [];
          }
        }
        newNodes = Utils.sort(newNodes, -1);
        this._inColumnResize = true;
        this.nodes = [];
        newNodes.forEach((node) => {
          this.addNode(node, false);
          delete node._orig;
        });
      }
      this.nodes.forEach((n) => delete n._orig);
      this.batchUpdate(false, !doCompact);
      delete this._inColumnResize;
      return this;
    }
    /**
     * call to cache the given layout internally to the given location so we can restore back when column changes size
     * @param nodes list of nodes
     * @param column corresponding column index to save it under
     * @param clear if true, will force other caches to be removed (default false)
     */
    cacheLayout(nodes, column, clear = false) {
      const copy = [];
      nodes.forEach((n, i) => {
        if (n._id === void 0) {
          const existing = n.id ? this.nodes.find((n2) => n2.id === n.id) : void 0;
          n._id = existing?._id ?? _GridStackEngine._idSeq++;
        }
        copy[i] = { x: n.x, y: n.y, w: n.w, _id: n._id };
      });
      this._layouts = clear ? [] : this._layouts || [];
      this._layouts[column] = copy;
      return this;
    }
    /**
     * call to cache the given node layout internally to the given location so we can restore back when column changes size
     * @param node single node to cache
     * @param column corresponding column index to save it under
     */
    cacheOneLayout(n, column) {
      n._id = n._id ?? _GridStackEngine._idSeq++;
      const l = { x: n.x, y: n.y, w: n.w, _id: n._id };
      if (n.autoPosition || n.x === void 0) {
        delete l.x;
        delete l.y;
        if (n.autoPosition)
          l.autoPosition = true;
      }
      this._layouts = this._layouts || [];
      this._layouts[column] = this._layouts[column] || [];
      const index = this.findCacheLayout(n, column);
      if (index === -1)
        this._layouts[column].push(l);
      else
        this._layouts[column][index] = l;
      return this;
    }
    findCacheLayout(n, column) {
      return this._layouts?.[column]?.findIndex((l) => l._id === n._id) ?? -1;
    }
    removeNodeFromLayoutCache(n) {
      if (!this._layouts) {
        return;
      }
      for (let i = 0; i < this._layouts.length; i++) {
        const index = this.findCacheLayout(n, i);
        if (index !== -1) {
          this._layouts[i].splice(index, 1);
        }
      }
    }
    /** called to remove all internal values but the _id */
    cleanupNode(node) {
      for (const prop in node) {
        if (prop[0] === "_" && prop !== "_id")
          delete node[prop];
      }
      return this;
    }
  };
  GridStackEngine._idSeq = 0;

  // node_modules/gridstack/dist/types.js
  var gridDefaults = {
    alwaysShowResizeHandle: "mobile",
    animate: true,
    auto: true,
    cellHeight: "auto",
    cellHeightThrottle: 100,
    cellHeightUnit: "px",
    column: 12,
    draggable: { handle: ".grid-stack-item-content", appendTo: "body", scroll: true },
    handle: ".grid-stack-item-content",
    itemClass: "grid-stack-item",
    margin: 10,
    marginUnit: "px",
    maxRow: 0,
    minRow: 0,
    placeholderClass: "grid-stack-placeholder",
    placeholderText: "",
    removableOptions: { accept: "grid-stack-item", decline: "grid-stack-non-removable" },
    resizable: { handles: "se" },
    rtl: "auto"
    // **** same as not being set ****
    // disableDrag: false,
    // disableResize: false,
    // float: false,
    // handleClass: null,
    // removable: false,
    // staticGrid: false,
    // styleInHead: false,
    //removable
  };

  // node_modules/gridstack/dist/dd-manager.js
  var DDManager = class {
  };

  // node_modules/gridstack/dist/dd-touch.js
  var isTouch = typeof window !== "undefined" && typeof document !== "undefined" && ("ontouchstart" in document || "ontouchstart" in window || window.DocumentTouch && document instanceof window.DocumentTouch || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0);
  var DDTouch = class {
  };
  function simulateMouseEvent(e, simulatedType) {
    if (e.touches.length > 1)
      return;
    if (e.cancelable)
      e.preventDefault();
    Utils.simulateMouseEvent(e.changedTouches[0], simulatedType);
  }
  function simulatePointerMouseEvent(e, simulatedType) {
    if (e.cancelable)
      e.preventDefault();
    Utils.simulateMouseEvent(e, simulatedType);
  }
  function touchstart(e) {
    if (DDTouch.touchHandled)
      return;
    DDTouch.touchHandled = true;
    simulateMouseEvent(e, "mousedown");
  }
  function touchmove(e) {
    if (!DDTouch.touchHandled)
      return;
    simulateMouseEvent(e, "mousemove");
  }
  function touchend(e) {
    if (!DDTouch.touchHandled)
      return;
    if (DDTouch.pointerLeaveTimeout) {
      window.clearTimeout(DDTouch.pointerLeaveTimeout);
      delete DDTouch.pointerLeaveTimeout;
    }
    const wasDragging = !!DDManager.dragElement;
    simulateMouseEvent(e, "mouseup");
    if (!wasDragging) {
      simulateMouseEvent(e, "click");
    }
    DDTouch.touchHandled = false;
  }
  function pointerdown(e) {
    if (e.pointerType === "mouse")
      return;
    e.target.releasePointerCapture(e.pointerId);
  }
  function pointerenter(e) {
    if (!DDManager.dragElement) {
      return;
    }
    if (e.pointerType === "mouse")
      return;
    simulatePointerMouseEvent(e, "mouseenter");
  }
  function pointerleave(e) {
    if (!DDManager.dragElement) {
      return;
    }
    if (e.pointerType === "mouse")
      return;
    DDTouch.pointerLeaveTimeout = window.setTimeout(() => {
      delete DDTouch.pointerLeaveTimeout;
      simulatePointerMouseEvent(e, "mouseleave");
    }, 10);
  }

  // node_modules/gridstack/dist/dd-resizable-handle.js
  var DDResizableHandle = class _DDResizableHandle {
    constructor(host, dir, option) {
      this.host = host;
      this.dir = dir;
      this.option = option;
      this.moving = false;
      this._mouseDown = this._mouseDown.bind(this);
      this._mouseMove = this._mouseMove.bind(this);
      this._mouseUp = this._mouseUp.bind(this);
      this._keyEvent = this._keyEvent.bind(this);
      this._init();
    }
    /** @internal */
    _init() {
      const el = this.el = document.createElement("div");
      el.classList.add("ui-resizable-handle");
      el.classList.add(`${_DDResizableHandle.prefix}${this.dir}`);
      el.style.zIndex = "100";
      el.style.userSelect = "none";
      this.host.appendChild(this.el);
      this.el.addEventListener("mousedown", this._mouseDown);
      if (isTouch) {
        this.el.addEventListener("touchstart", touchstart);
        this.el.addEventListener("pointerdown", pointerdown);
      }
      return this;
    }
    /** call this when resize handle needs to be removed and cleaned up */
    destroy() {
      if (this.moving)
        this._mouseUp(this.mouseDownEvent);
      this.el.removeEventListener("mousedown", this._mouseDown);
      if (isTouch) {
        this.el.removeEventListener("touchstart", touchstart);
        this.el.removeEventListener("pointerdown", pointerdown);
      }
      this.host.removeChild(this.el);
      delete this.el;
      delete this.host;
      return this;
    }
    /** @internal called on mouse down on us: capture move on the entire document (mouse might not stay on us) until we release the mouse */
    _mouseDown(e) {
      this.mouseDownEvent = e;
      document.addEventListener("mousemove", this._mouseMove, { capture: true, passive: true });
      document.addEventListener("mouseup", this._mouseUp, true);
      if (isTouch) {
        this.el.addEventListener("touchmove", touchmove);
        this.el.addEventListener("touchend", touchend);
      }
      e.stopPropagation();
      e.preventDefault();
    }
    /** @internal */
    _mouseMove(e) {
      const s = this.mouseDownEvent;
      if (this.moving) {
        this._triggerEvent("move", e);
      } else if (Math.abs(e.x - s.x) + Math.abs(e.y - s.y) > 2) {
        this.moving = true;
        this._triggerEvent("start", this.mouseDownEvent);
        this._triggerEvent("move", e);
        document.addEventListener("keydown", this._keyEvent);
      }
      e.stopPropagation();
    }
    /** @internal */
    _mouseUp(e) {
      if (this.moving) {
        this._triggerEvent("stop", e);
        document.removeEventListener("keydown", this._keyEvent);
      }
      document.removeEventListener("mousemove", this._mouseMove, true);
      document.removeEventListener("mouseup", this._mouseUp, true);
      if (isTouch) {
        this.el.removeEventListener("touchmove", touchmove);
        this.el.removeEventListener("touchend", touchend);
      }
      delete this.moving;
      delete this.mouseDownEvent;
      e.stopPropagation();
      e.preventDefault();
    }
    /** @internal call when keys are being pressed - use Esc to cancel */
    _keyEvent(e) {
      if (e.key === "Escape") {
        this.host.gridstackNode?.grid?.engine.restoreInitial();
        this._mouseUp(this.mouseDownEvent);
      }
    }
    /** @internal */
    _triggerEvent(name, event) {
      if (this.option[name])
        this.option[name](event);
      return this;
    }
  };
  DDResizableHandle.prefix = "ui-resizable-";

  // node_modules/gridstack/dist/dd-base-impl.js
  var DDBaseImplement = class {
    constructor() {
      this._eventRegister = {};
    }
    /** returns the enable state, but you have to call enable()/disable() to change (as other things need to happen) */
    get disabled() {
      return this._disabled;
    }
    on(event, callback) {
      this._eventRegister[event] = callback;
    }
    off(event) {
      delete this._eventRegister[event];
    }
    enable() {
      this._disabled = false;
    }
    disable() {
      this._disabled = true;
    }
    destroy() {
      delete this._eventRegister;
    }
    triggerEvent(eventName, event) {
      if (!this.disabled && this._eventRegister && this._eventRegister[eventName])
        return this._eventRegister[eventName](event);
    }
  };

  // node_modules/gridstack/dist/dd-resizable.js
  var DDResizable = class _DDResizable extends DDBaseImplement {
    // have to be public else complains for HTMLElementExtendOpt ?
    constructor(el, option = {}) {
      super();
      this.el = el;
      this.option = option;
      this.rectScale = { x: 1, y: 1 };
      this._ui = () => {
        const containmentEl = this.el.parentElement;
        const containmentRect = containmentEl.getBoundingClientRect();
        const newRect = {
          width: this.originalRect.width,
          height: this.originalRect.height + this.scrolled,
          left: this.originalRect.left,
          top: this.originalRect.top - this.scrolled
        };
        const rect = this.temporalRect || newRect;
        return {
          position: {
            left: (rect.left - containmentRect.left) * this.rectScale.x,
            top: (rect.top - containmentRect.top) * this.rectScale.y
          },
          size: {
            width: rect.width * this.rectScale.x,
            height: rect.height * this.rectScale.y
          }
          /* Gridstack ONLY needs position set above... keep around in case.
          element: [this.el], // The object representing the element to be resized
          helper: [], // TODO: not support yet - The object representing the helper that's being resized
          originalElement: [this.el],// we don't wrap here, so simplify as this.el //The object representing the original element before it is wrapped
          originalPosition: { // The position represented as { left, top } before the resizable is resized
            left: this.originalRect.left - containmentRect.left,
            top: this.originalRect.top - containmentRect.top
          },
          originalSize: { // The size represented as { width, height } before the resizable is resized
            width: this.originalRect.width,
            height: this.originalRect.height
          }
          */
        };
      };
      this._mouseOver = this._mouseOver.bind(this);
      this._mouseOut = this._mouseOut.bind(this);
      this.enable();
      this._setupAutoHide(this.option.autoHide);
      this._setupHandlers();
    }
    on(event, callback) {
      super.on(event, callback);
    }
    off(event) {
      super.off(event);
    }
    enable() {
      super.enable();
      this.el.classList.remove("ui-resizable-disabled");
      this._setupAutoHide(this.option.autoHide);
    }
    disable() {
      super.disable();
      this.el.classList.add("ui-resizable-disabled");
      this._setupAutoHide(false);
    }
    destroy() {
      this._removeHandlers();
      this._setupAutoHide(false);
      delete this.el;
      super.destroy();
    }
    updateOption(opts) {
      const updateHandles = opts.handles && opts.handles !== this.option.handles;
      const updateAutoHide = opts.autoHide && opts.autoHide !== this.option.autoHide;
      Object.keys(opts).forEach((key) => this.option[key] = opts[key]);
      if (updateHandles) {
        this._removeHandlers();
        this._setupHandlers();
      }
      if (updateAutoHide) {
        this._setupAutoHide(this.option.autoHide);
      }
      return this;
    }
    /** @internal turns auto hide on/off */
    _setupAutoHide(auto) {
      if (auto) {
        this.el.classList.add("ui-resizable-autohide");
        this.el.addEventListener("mouseover", this._mouseOver);
        this.el.addEventListener("mouseout", this._mouseOut);
      } else {
        this.el.classList.remove("ui-resizable-autohide");
        this.el.removeEventListener("mouseover", this._mouseOver);
        this.el.removeEventListener("mouseout", this._mouseOut);
        if (DDManager.overResizeElement === this) {
          delete DDManager.overResizeElement;
        }
      }
      return this;
    }
    /** @internal */
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _mouseOver(e) {
      if (DDManager.overResizeElement || DDManager.dragElement)
        return;
      DDManager.overResizeElement = this;
      this.el.classList.remove("ui-resizable-autohide");
    }
    /** @internal */
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _mouseOut(e) {
      if (DDManager.overResizeElement !== this)
        return;
      delete DDManager.overResizeElement;
      this.el.classList.add("ui-resizable-autohide");
    }
    /** @internal */
    _setupHandlers() {
      this.handlers = this.option.handles.split(",").map((dir) => dir.trim()).map((dir) => new DDResizableHandle(this.el, dir, {
        start: (event) => {
          this._resizeStart(event);
        },
        stop: (event) => {
          this._resizeStop(event);
        },
        move: (event) => {
          this._resizing(event, dir);
        }
      }));
      return this;
    }
    /** @internal */
    _resizeStart(event) {
      this.sizeToContent = Utils.shouldSizeToContent(this.el.gridstackNode, true);
      this.originalRect = this.el.getBoundingClientRect();
      this.scrollEl = Utils.getScrollElement(this.el);
      this.scrollY = this.scrollEl.scrollTop;
      this.scrolled = 0;
      this.startEvent = event;
      this._setupHelper();
      this._applyChange();
      const ev = Utils.initEvent(event, { type: "resizestart", target: this.el });
      if (this.option.start) {
        this.option.start(ev, this._ui());
      }
      this.el.classList.add("ui-resizable-resizing");
      this.triggerEvent("resizestart", ev);
      return this;
    }
    /** @internal */
    _resizing(event, dir) {
      this.scrolled = this.scrollEl.scrollTop - this.scrollY;
      this.temporalRect = this._getChange(event, dir);
      this._applyChange();
      const ev = Utils.initEvent(event, { type: "resize", target: this.el });
      if (this.option.resize) {
        this.option.resize(ev, this._ui());
      }
      this.triggerEvent("resize", ev);
      return this;
    }
    /** @internal */
    _resizeStop(event) {
      const ev = Utils.initEvent(event, { type: "resizestop", target: this.el });
      if (this.option.stop) {
        this.option.stop(ev);
      }
      this.el.classList.remove("ui-resizable-resizing");
      this.triggerEvent("resizestop", ev);
      this._cleanHelper();
      delete this.startEvent;
      delete this.originalRect;
      delete this.temporalRect;
      delete this.scrollY;
      delete this.scrolled;
      return this;
    }
    /** @internal */
    _setupHelper() {
      this.elOriginStyleVal = _DDResizable._originStyleProp.map((prop) => this.el.style[prop]);
      this.parentOriginStylePosition = this.el.parentElement.style.position;
      const parent = this.el.parentElement;
      const dragTransform = Utils.getValuesFromTransformedElement(parent);
      this.rectScale = {
        x: dragTransform.xScale,
        y: dragTransform.yScale
      };
      if (getComputedStyle(this.el.parentElement).position.match(/static/)) {
        this.el.parentElement.style.position = "relative";
      }
      this.el.style.position = "absolute";
      this.el.style.opacity = "0.8";
      return this;
    }
    /** @internal */
    _cleanHelper() {
      _DDResizable._originStyleProp.forEach((prop, i) => {
        this.el.style[prop] = this.elOriginStyleVal[i] || null;
      });
      this.el.parentElement.style.position = this.parentOriginStylePosition || null;
      return this;
    }
    /** @internal */
    _getChange(event, dir) {
      const oEvent = this.startEvent;
      const newRect = {
        width: this.originalRect.width,
        height: this.originalRect.height + this.scrolled,
        left: this.originalRect.left,
        top: this.originalRect.top - this.scrolled
      };
      const offsetX = event.clientX - oEvent.clientX;
      const offsetY = this.sizeToContent ? 0 : event.clientY - oEvent.clientY;
      let moveLeft;
      let moveUp;
      if (dir.indexOf("e") > -1) {
        newRect.width += offsetX;
      } else if (dir.indexOf("w") > -1) {
        newRect.width -= offsetX;
        newRect.left += offsetX;
        moveLeft = true;
      }
      if (dir.indexOf("s") > -1) {
        newRect.height += offsetY;
      } else if (dir.indexOf("n") > -1) {
        newRect.height -= offsetY;
        newRect.top += offsetY;
        moveUp = true;
      }
      const constrain = this._constrainSize(newRect.width, newRect.height, moveLeft, moveUp);
      if (Math.round(newRect.width) !== Math.round(constrain.width)) {
        if (dir.indexOf("w") > -1) {
          newRect.left += newRect.width - constrain.width;
        }
        newRect.width = constrain.width;
      }
      if (Math.round(newRect.height) !== Math.round(constrain.height)) {
        if (dir.indexOf("n") > -1) {
          newRect.top += newRect.height - constrain.height;
        }
        newRect.height = constrain.height;
      }
      return newRect;
    }
    /** @internal constrain the size to the set min/max values */
    _constrainSize(oWidth, oHeight, moveLeft, moveUp) {
      const o = this.option;
      const maxWidth = (moveLeft ? o.maxWidthMoveLeft : o.maxWidth) || Number.MAX_SAFE_INTEGER;
      const minWidth = o.minWidth / this.rectScale.x || oWidth;
      const maxHeight = (moveUp ? o.maxHeightMoveUp : o.maxHeight) || Number.MAX_SAFE_INTEGER;
      const minHeight = o.minHeight / this.rectScale.y || oHeight;
      const width = Math.min(maxWidth, Math.max(minWidth, oWidth));
      const height = Math.min(maxHeight, Math.max(minHeight, oHeight));
      return { width, height };
    }
    /** @internal */
    _applyChange() {
      let containmentRect = { left: 0, top: 0, width: 0, height: 0 };
      if (this.el.style.position === "absolute") {
        const containmentEl = this.el.parentElement;
        const { left, top } = containmentEl.getBoundingClientRect();
        containmentRect = { left, top, width: 0, height: 0 };
      }
      if (!this.temporalRect)
        return this;
      Object.keys(this.temporalRect).forEach((key) => {
        const value = this.temporalRect[key];
        const scaleReciprocal = key === "width" || key === "left" ? this.rectScale.x : key === "height" || key === "top" ? this.rectScale.y : 1;
        this.el.style[key] = (value - containmentRect[key]) * scaleReciprocal + "px";
      });
      return this;
    }
    /** @internal */
    _removeHandlers() {
      this.handlers.forEach((handle) => handle.destroy());
      delete this.handlers;
      return this;
    }
  };
  DDResizable._originStyleProp = ["width", "height", "position", "left", "top", "opacity", "zIndex"];

  // node_modules/gridstack/dist/dd-draggable.js
  var skipMouseDown = 'input,textarea,button,select,option,[contenteditable="true"],.ui-resizable-handle';
  var DDDraggable = class _DDDraggable extends DDBaseImplement {
    constructor(el, option = {}) {
      super();
      this.el = el;
      this.option = option;
      this.dragTransform = {
        xScale: 1,
        yScale: 1,
        xOffset: 0,
        yOffset: 0
      };
      const handleName = option?.handle?.substring(1);
      const n = el.gridstackNode;
      this.dragEls = !handleName || el.classList.contains(handleName) ? [el] : n?.subGrid ? [el.querySelector(option.handle) || el] : Array.from(el.querySelectorAll(option.handle));
      if (this.dragEls.length === 0) {
        this.dragEls = [el];
      }
      this._mouseDown = this._mouseDown.bind(this);
      this._mouseMove = this._mouseMove.bind(this);
      this._mouseUp = this._mouseUp.bind(this);
      this._keyEvent = this._keyEvent.bind(this);
      this.enable();
    }
    on(event, callback) {
      super.on(event, callback);
    }
    off(event) {
      super.off(event);
    }
    enable() {
      if (this.disabled === false)
        return;
      super.enable();
      this.dragEls.forEach((dragEl) => {
        dragEl.addEventListener("mousedown", this._mouseDown);
        if (isTouch) {
          dragEl.addEventListener("touchstart", touchstart);
          dragEl.addEventListener("pointerdown", pointerdown);
        }
      });
      this.el.classList.remove("ui-draggable-disabled");
    }
    disable(forDestroy = false) {
      if (this.disabled === true)
        return;
      super.disable();
      this.dragEls.forEach((dragEl) => {
        dragEl.removeEventListener("mousedown", this._mouseDown);
        if (isTouch) {
          dragEl.removeEventListener("touchstart", touchstart);
          dragEl.removeEventListener("pointerdown", pointerdown);
        }
      });
      if (!forDestroy)
        this.el.classList.add("ui-draggable-disabled");
    }
    destroy() {
      if (this.dragTimeout)
        window.clearTimeout(this.dragTimeout);
      delete this.dragTimeout;
      if (this.mouseDownEvent)
        this._mouseUp(this.mouseDownEvent);
      this.disable(true);
      delete this.el;
      delete this.helper;
      delete this.option;
      super.destroy();
    }
    updateOption(opts) {
      Object.keys(opts).forEach((key) => this.option[key] = opts[key]);
      return this;
    }
    /** @internal call when mouse goes down before a dragstart happens */
    _mouseDown(e) {
      if (DDManager.mouseHandled)
        return;
      if (e.button !== 0)
        return true;
      if (!this.dragEls.find((el) => el === e.target) && e.target.closest(skipMouseDown))
        return true;
      if (this.option.cancel) {
        if (e.target.closest(this.option.cancel))
          return true;
      }
      this.mouseDownEvent = e;
      delete this.dragging;
      delete DDManager.dragElement;
      delete DDManager.dropElement;
      document.addEventListener("mousemove", this._mouseMove, { capture: true, passive: true });
      document.addEventListener("mouseup", this._mouseUp, true);
      if (isTouch) {
        e.currentTarget.addEventListener("touchmove", touchmove);
        e.currentTarget.addEventListener("touchend", touchend);
      }
      e.preventDefault();
      if (document.activeElement)
        document.activeElement.blur();
      DDManager.mouseHandled = true;
      return true;
    }
    /** @internal method to call actual drag event */
    _callDrag(e) {
      if (!this.dragging)
        return;
      const ev = Utils.initEvent(e, { target: this.el, type: "drag" });
      if (this.option.drag) {
        this.option.drag(ev, this.ui());
      }
      this.triggerEvent("drag", ev);
    }
    /** @internal called when the main page (after successful mousedown) receives a move event to drag the item around the screen */
    _mouseMove(e) {
      const s = this.mouseDownEvent;
      this.lastDrag = e;
      if (this.dragging) {
        this._dragFollow(e);
        if (DDManager.pauseDrag) {
          const pause = Number.isInteger(DDManager.pauseDrag) ? DDManager.pauseDrag : 100;
          if (this.dragTimeout)
            window.clearTimeout(this.dragTimeout);
          this.dragTimeout = window.setTimeout(() => this._callDrag(e), pause);
        } else {
          this._callDrag(e);
        }
      } else if (Math.abs(e.x - s.x) + Math.abs(e.y - s.y) > 3) {
        this.dragging = true;
        DDManager.dragElement = this;
        const grid2 = this.el.gridstackNode?.grid;
        if (grid2) {
          DDManager.dropElement = grid2.el.ddElement.ddDroppable;
        } else {
          delete DDManager.dropElement;
        }
        this.helper = this._createHelper();
        this._setupHelperContainmentStyle();
        this.dragTransform = Utils.getValuesFromTransformedElement(this.helperContainment);
        this.dragOffset = this._getDragOffset(e, this.el, this.helperContainment);
        this._setupHelperStyle(e);
        const ev = Utils.initEvent(e, { target: this.el, type: "dragstart" });
        if (this.option.start) {
          this.option.start(ev, this.ui());
        }
        this.triggerEvent("dragstart", ev);
        document.addEventListener("keydown", this._keyEvent);
      }
      return true;
    }
    /** @internal call when the mouse gets released to drop the item at current location */
    _mouseUp(e) {
      document.removeEventListener("mousemove", this._mouseMove, true);
      document.removeEventListener("mouseup", this._mouseUp, true);
      if (isTouch && e.currentTarget) {
        e.currentTarget.removeEventListener("touchmove", touchmove, true);
        e.currentTarget.removeEventListener("touchend", touchend, true);
      }
      if (this.dragging) {
        delete this.dragging;
        delete this.el.gridstackNode?._origRotate;
        document.removeEventListener("keydown", this._keyEvent);
        if (DDManager.dropElement?.el === this.el.parentElement) {
          delete DDManager.dropElement;
        }
        this.helperContainment.style.position = this.parentOriginStylePosition || null;
        if (this.helper !== this.el)
          this.helper.remove();
        this._removeHelperStyle();
        const ev = Utils.initEvent(e, { target: this.el, type: "dragstop" });
        if (this.option.stop) {
          this.option.stop(ev);
        }
        this.triggerEvent("dragstop", ev);
        if (DDManager.dropElement) {
          DDManager.dropElement.drop(e);
        }
      }
      delete this.helper;
      delete this.mouseDownEvent;
      delete DDManager.dragElement;
      delete DDManager.dropElement;
      delete DDManager.mouseHandled;
      e.preventDefault();
    }
    /** @internal call when keys are being pressed - use Esc to cancel, R to rotate */
    _keyEvent(e) {
      const n = this.el.gridstackNode;
      const grid2 = n?.grid || DDManager.dropElement?.el?.gridstack;
      if (e.key === "Escape") {
        if (n && n._origRotate) {
          n._orig = n._origRotate;
          delete n._origRotate;
        }
        grid2?.cancelDrag();
        this._mouseUp(this.mouseDownEvent);
      } else if (n && grid2 && (e.key === "r" || e.key === "R")) {
        if (!Utils.canBeRotated(n))
          return;
        n._origRotate = n._origRotate || { ...n._orig };
        delete n._moving;
        grid2.setAnimation(false).rotate(n.el, { top: -this.dragOffset.offsetTop, left: -this.dragOffset.offsetLeft }).setAnimation();
        n._moving = true;
        this.dragOffset = this._getDragOffset(this.lastDrag, n.el, this.helperContainment);
        this.helper.style.width = this.dragOffset.width + "px";
        this.helper.style.height = this.dragOffset.height + "px";
        Utils.swap(n._orig, "w", "h");
        delete n._rect;
        this._mouseMove(this.lastDrag);
      }
    }
    /** @internal create a clone copy (or user defined method) of the original drag item if set */
    _createHelper() {
      let helper = this.el;
      if (typeof this.option.helper === "function") {
        helper = this.option.helper(this.el);
      } else if (this.option.helper === "clone") {
        helper = Utils.cloneNode(this.el);
      }
      if (!helper.parentElement) {
        Utils.appendTo(helper, this.option.appendTo === "parent" ? this.el.parentElement : this.option.appendTo);
      }
      this.dragElementOriginStyle = _DDDraggable.originStyleProp.map((prop) => this.el.style[prop]);
      return helper;
    }
    /** @internal set the fix position of the dragged item */
    _setupHelperStyle(e) {
      this.helper.classList.add("ui-draggable-dragging");
      const style = this.helper.style;
      style.pointerEvents = "none";
      style.width = this.dragOffset.width + "px";
      style.height = this.dragOffset.height + "px";
      style.willChange = "left, top";
      style.position = "fixed";
      this._dragFollow(e);
      style.transition = "none";
      setTimeout(() => {
        if (this.helper) {
          style.transition = null;
        }
      }, 0);
      return this;
    }
    /** @internal restore back the original style before dragging */
    _removeHelperStyle() {
      this.helper.classList.remove("ui-draggable-dragging");
      const node = this.helper?.gridstackNode;
      if (!node?._isAboutToRemove && this.dragElementOriginStyle) {
        const helper = this.helper;
        const transition = this.dragElementOriginStyle["transition"] || null;
        helper.style.transition = this.dragElementOriginStyle["transition"] = "none";
        _DDDraggable.originStyleProp.forEach((prop) => helper.style[prop] = this.dragElementOriginStyle[prop] || null);
        setTimeout(() => helper.style.transition = transition, 50);
      }
      delete this.dragElementOriginStyle;
      return this;
    }
    /** @internal updates the top/left position to follow the mouse */
    _dragFollow(e) {
      const containmentRect = { left: 0, top: 0 };
      const style = this.helper.style;
      const offset = this.dragOffset;
      style.left = (e.clientX + offset.offsetLeft - containmentRect.left) * this.dragTransform.xScale + "px";
      style.top = (e.clientY + offset.offsetTop - containmentRect.top) * this.dragTransform.yScale + "px";
    }
    /** @internal */
    _setupHelperContainmentStyle() {
      this.helperContainment = this.helper.parentElement;
      if (this.helper.style.position !== "fixed") {
        this.parentOriginStylePosition = this.helperContainment.style.position;
        if (getComputedStyle(this.helperContainment).position.match(/static/)) {
          this.helperContainment.style.position = "relative";
        }
      }
      return this;
    }
    /** @internal */
    _getDragOffset(event, el, parent) {
      let xformOffsetX = 0;
      let xformOffsetY = 0;
      if (parent) {
        xformOffsetX = this.dragTransform.xOffset;
        xformOffsetY = this.dragTransform.yOffset;
      }
      const targetOffset = el.getBoundingClientRect();
      return {
        left: targetOffset.left,
        top: targetOffset.top,
        offsetLeft: -event.clientX + targetOffset.left - xformOffsetX,
        offsetTop: -event.clientY + targetOffset.top - xformOffsetY,
        width: targetOffset.width * this.dragTransform.xScale,
        height: targetOffset.height * this.dragTransform.yScale
      };
    }
    /** @internal TODO: set to public as called by DDDroppable! */
    ui() {
      const containmentEl = this.el.parentElement;
      const containmentRect = containmentEl.getBoundingClientRect();
      const offset = this.helper.getBoundingClientRect();
      return {
        position: {
          top: (offset.top - containmentRect.top) * this.dragTransform.yScale,
          left: (offset.left - containmentRect.left) * this.dragTransform.xScale
        }
        /* not used by GridStack for now...
        helper: [this.helper], //The object arr representing the helper that's being dragged.
        offset: { top: offset.top, left: offset.left } // Current offset position of the helper as { top, left } object.
        */
      };
    }
  };
  DDDraggable.originStyleProp = ["width", "height", "transform", "transform-origin", "transition", "pointerEvents", "position", "left", "top", "minWidth", "willChange"];

  // node_modules/gridstack/dist/dd-droppable.js
  var DDDroppable = class extends DDBaseImplement {
    constructor(el, option = {}) {
      super();
      this.el = el;
      this.option = option;
      this._mouseEnter = this._mouseEnter.bind(this);
      this._mouseLeave = this._mouseLeave.bind(this);
      this.enable();
      this._setupAccept();
    }
    on(event, callback) {
      super.on(event, callback);
    }
    off(event) {
      super.off(event);
    }
    enable() {
      if (this.disabled === false)
        return;
      super.enable();
      this.el.classList.add("ui-droppable");
      this.el.classList.remove("ui-droppable-disabled");
      this.el.addEventListener("mouseenter", this._mouseEnter);
      this.el.addEventListener("mouseleave", this._mouseLeave);
      if (isTouch) {
        this.el.addEventListener("pointerenter", pointerenter);
        this.el.addEventListener("pointerleave", pointerleave);
      }
    }
    disable(forDestroy = false) {
      if (this.disabled === true)
        return;
      super.disable();
      this.el.classList.remove("ui-droppable");
      if (!forDestroy)
        this.el.classList.add("ui-droppable-disabled");
      this.el.removeEventListener("mouseenter", this._mouseEnter);
      this.el.removeEventListener("mouseleave", this._mouseLeave);
      if (isTouch) {
        this.el.removeEventListener("pointerenter", pointerenter);
        this.el.removeEventListener("pointerleave", pointerleave);
      }
    }
    destroy() {
      this.disable(true);
      this.el.classList.remove("ui-droppable");
      this.el.classList.remove("ui-droppable-disabled");
      super.destroy();
    }
    updateOption(opts) {
      Object.keys(opts).forEach((key) => this.option[key] = opts[key]);
      this._setupAccept();
      return this;
    }
    /** @internal called when the cursor enters our area - prepare for a possible drop and track leaving */
    _mouseEnter(e) {
      if (!DDManager.dragElement)
        return;
      if (!this._canDrop(DDManager.dragElement.el))
        return;
      e.preventDefault();
      e.stopPropagation();
      if (DDManager.dropElement && DDManager.dropElement !== this) {
        DDManager.dropElement._mouseLeave(e, true);
      }
      DDManager.dropElement = this;
      const ev = Utils.initEvent(e, { target: this.el, type: "dropover" });
      if (this.option.over) {
        this.option.over(ev, this._ui(DDManager.dragElement));
      }
      this.triggerEvent("dropover", ev);
      this.el.classList.add("ui-droppable-over");
    }
    /** @internal called when the item is leaving our area, stop tracking if we had moving item */
    _mouseLeave(e, calledByEnter = false) {
      if (!DDManager.dragElement || DDManager.dropElement !== this)
        return;
      e.preventDefault();
      e.stopPropagation();
      const ev = Utils.initEvent(e, { target: this.el, type: "dropout" });
      if (this.option.out) {
        this.option.out(ev, this._ui(DDManager.dragElement));
      }
      this.triggerEvent("dropout", ev);
      if (DDManager.dropElement === this) {
        delete DDManager.dropElement;
        if (!calledByEnter) {
          let parentDrop;
          let parent = this.el.parentElement;
          while (!parentDrop && parent) {
            parentDrop = parent.ddElement?.ddDroppable;
            parent = parent.parentElement;
          }
          if (parentDrop) {
            parentDrop._mouseEnter(e);
          }
        }
      }
    }
    /** item is being dropped on us - called by the drag mouseup handler - this calls the client drop event */
    drop(e) {
      e.preventDefault();
      const ev = Utils.initEvent(e, { target: this.el, type: "drop" });
      if (this.option.drop) {
        this.option.drop(ev, this._ui(DDManager.dragElement));
      }
      this.triggerEvent("drop", ev);
    }
    /** @internal true if element matches the string/method accept option */
    _canDrop(el) {
      return el && (!this.accept || this.accept(el));
    }
    /** @internal */
    _setupAccept() {
      if (!this.option.accept)
        return this;
      if (typeof this.option.accept === "string") {
        this.accept = (el) => el.classList.contains(this.option.accept) || el.matches(this.option.accept);
      } else {
        this.accept = this.option.accept;
      }
      return this;
    }
    /** @internal */
    _ui(drag) {
      return {
        draggable: drag.el,
        ...drag.ui()
      };
    }
  };

  // node_modules/gridstack/dist/dd-element.js
  var DDElement = class _DDElement {
    static init(el) {
      if (!el.ddElement) {
        el.ddElement = new _DDElement(el);
      }
      return el.ddElement;
    }
    constructor(el) {
      this.el = el;
    }
    on(eventName, callback) {
      if (this.ddDraggable && ["drag", "dragstart", "dragstop"].indexOf(eventName) > -1) {
        this.ddDraggable.on(eventName, callback);
      } else if (this.ddDroppable && ["drop", "dropover", "dropout"].indexOf(eventName) > -1) {
        this.ddDroppable.on(eventName, callback);
      } else if (this.ddResizable && ["resizestart", "resize", "resizestop"].indexOf(eventName) > -1) {
        this.ddResizable.on(eventName, callback);
      }
      return this;
    }
    off(eventName) {
      if (this.ddDraggable && ["drag", "dragstart", "dragstop"].indexOf(eventName) > -1) {
        this.ddDraggable.off(eventName);
      } else if (this.ddDroppable && ["drop", "dropover", "dropout"].indexOf(eventName) > -1) {
        this.ddDroppable.off(eventName);
      } else if (this.ddResizable && ["resizestart", "resize", "resizestop"].indexOf(eventName) > -1) {
        this.ddResizable.off(eventName);
      }
      return this;
    }
    setupDraggable(opts) {
      if (!this.ddDraggable) {
        this.ddDraggable = new DDDraggable(this.el, opts);
      } else {
        this.ddDraggable.updateOption(opts);
      }
      return this;
    }
    cleanDraggable() {
      if (this.ddDraggable) {
        this.ddDraggable.destroy();
        delete this.ddDraggable;
      }
      return this;
    }
    setupResizable(opts) {
      if (!this.ddResizable) {
        this.ddResizable = new DDResizable(this.el, opts);
      } else {
        this.ddResizable.updateOption(opts);
      }
      return this;
    }
    cleanResizable() {
      if (this.ddResizable) {
        this.ddResizable.destroy();
        delete this.ddResizable;
      }
      return this;
    }
    setupDroppable(opts) {
      if (!this.ddDroppable) {
        this.ddDroppable = new DDDroppable(this.el, opts);
      } else {
        this.ddDroppable.updateOption(opts);
      }
      return this;
    }
    cleanDroppable() {
      if (this.ddDroppable) {
        this.ddDroppable.destroy();
        delete this.ddDroppable;
      }
      return this;
    }
  };

  // node_modules/gridstack/dist/dd-gridstack.js
  var DDGridStack = class {
    resizable(el, opts, key, value) {
      this._getDDElements(el, opts).forEach((dEl) => {
        if (opts === "disable" || opts === "enable") {
          dEl.ddResizable && dEl.ddResizable[opts]();
        } else if (opts === "destroy") {
          dEl.ddResizable && dEl.cleanResizable();
        } else if (opts === "option") {
          dEl.setupResizable({ [key]: value });
        } else {
          const n = dEl.el.gridstackNode;
          const grid2 = n.grid;
          let handles = dEl.el.getAttribute("gs-resize-handles") || grid2.opts.resizable.handles || "e,s,se";
          if (handles === "all")
            handles = "n,e,s,w,se,sw,ne,nw";
          const autoHide = !grid2.opts.alwaysShowResizeHandle;
          dEl.setupResizable({
            ...grid2.opts.resizable,
            ...{ handles, autoHide },
            ...{
              start: opts.start,
              stop: opts.stop,
              resize: opts.resize
            }
          });
        }
      });
      return this;
    }
    draggable(el, opts, key, value) {
      this._getDDElements(el, opts).forEach((dEl) => {
        if (opts === "disable" || opts === "enable") {
          dEl.ddDraggable && dEl.ddDraggable[opts]();
        } else if (opts === "destroy") {
          dEl.ddDraggable && dEl.cleanDraggable();
        } else if (opts === "option") {
          dEl.setupDraggable({ [key]: value });
        } else {
          const grid2 = dEl.el.gridstackNode.grid;
          dEl.setupDraggable({
            ...grid2.opts.draggable,
            ...{
              // containment: (grid.parentGridNode && grid.opts.dragOut === false) ? grid.el.parentElement : (grid.opts.draggable.containment || null),
              start: opts.start,
              stop: opts.stop,
              drag: opts.drag
            }
          });
        }
      });
      return this;
    }
    dragIn(el, opts) {
      this._getDDElements(el).forEach((dEl) => dEl.setupDraggable(opts));
      return this;
    }
    droppable(el, opts, key, value) {
      if (typeof opts.accept === "function" && !opts._accept) {
        opts._accept = opts.accept;
        opts.accept = (el2) => opts._accept(el2);
      }
      this._getDDElements(el, opts).forEach((dEl) => {
        if (opts === "disable" || opts === "enable") {
          dEl.ddDroppable && dEl.ddDroppable[opts]();
        } else if (opts === "destroy") {
          dEl.ddDroppable && dEl.cleanDroppable();
        } else if (opts === "option") {
          dEl.setupDroppable({ [key]: value });
        } else {
          dEl.setupDroppable(opts);
        }
      });
      return this;
    }
    /** true if element is droppable */
    isDroppable(el) {
      return !!(el?.ddElement?.ddDroppable && !el.ddElement.ddDroppable.disabled);
    }
    /** true if element is draggable */
    isDraggable(el) {
      return !!(el?.ddElement?.ddDraggable && !el.ddElement.ddDraggable.disabled);
    }
    /** true if element is draggable */
    isResizable(el) {
      return !!(el?.ddElement?.ddResizable && !el.ddElement.ddResizable.disabled);
    }
    on(el, name, callback) {
      this._getDDElements(el).forEach((dEl) => dEl.on(name, (event) => {
        callback(event, DDManager.dragElement ? DDManager.dragElement.el : event.target, DDManager.dragElement ? DDManager.dragElement.helper : null);
      }));
      return this;
    }
    off(el, name) {
      this._getDDElements(el).forEach((dEl) => dEl.off(name));
      return this;
    }
    /** @internal returns a list of DD elements, creating them on the fly by default unless option is to destroy or disable */
    _getDDElements(els, opts) {
      const create = els.gridstack || opts !== "destroy" && opts !== "disable";
      const hosts = Utils.getElements(els);
      if (!hosts.length)
        return [];
      const list = hosts.map((e) => e.ddElement || (create ? DDElement.init(e) : null)).filter((d) => d);
      return list;
    }
  };

  // node_modules/gridstack/dist/gridstack.js
  var dd = new DDGridStack();
  var GridStack = class _GridStack {
    /**
     * initializing the HTML element, or selector string, into a grid will return the grid. Calling it again will
     * simply return the existing instance (ignore any passed options). There is also an initAll() version that support
     * multiple grids initialization at once. Or you can use addGrid() to create the entire grid from JSON.
     * @param options grid options (optional)
     * @param elOrString element or CSS selector (first one used) to convert to a grid (default to '.grid-stack' class selector)
     *
     * @example
     * const grid = GridStack.init();
     *
     * Note: the HTMLElement (of type GridHTMLElement) will store a `gridstack: GridStack` value that can be retrieve later
     * const grid = document.querySelector('.grid-stack').gridstack;
     */
    static init(options = {}, elOrString = ".grid-stack") {
      if (typeof document === "undefined")
        return null;
      const el = _GridStack.getGridElement(elOrString);
      if (!el) {
        if (typeof elOrString === "string") {
          console.error('GridStack.initAll() no grid was found with selector "' + elOrString + '" - element missing or wrong selector ?\nNote: ".grid-stack" is required for proper CSS styling and drag/drop, and is the default selector.');
        } else {
          console.error("GridStack.init() no grid element was passed.");
        }
        return null;
      }
      if (!el.gridstack) {
        el.gridstack = new _GridStack(el, Utils.cloneDeep(options));
      }
      return el.gridstack;
    }
    /**
     * Will initialize a list of elements (given a selector) and return an array of grids.
     * @param options grid options (optional)
     * @param selector elements selector to convert to grids (default to '.grid-stack' class selector)
     *
     * @example
     * const grids = GridStack.initAll();
     * grids.forEach(...)
     */
    static initAll(options = {}, selector = ".grid-stack") {
      const grids = [];
      if (typeof document === "undefined")
        return grids;
      _GridStack.getGridElements(selector).forEach((el) => {
        if (!el.gridstack) {
          el.gridstack = new _GridStack(el, Utils.cloneDeep(options));
        }
        grids.push(el.gridstack);
      });
      if (grids.length === 0) {
        console.error('GridStack.initAll() no grid was found with selector "' + selector + '" - element missing or wrong selector ?\nNote: ".grid-stack" is required for proper CSS styling and drag/drop, and is the default selector.');
      }
      return grids;
    }
    /**
     * call to create a grid with the given options, including loading any children from JSON structure. This will call GridStack.init(), then
     * grid.load() on any passed children (recursively). Great alternative to calling init() if you want entire grid to come from
     * JSON serialized data, including options.
     * @param parent HTML element parent to the grid
     * @param opt grids options used to initialize the grid, and list of children
     */
    static addGrid(parent, opt = {}) {
      if (!parent)
        return null;
      let el = parent;
      if (el.gridstack) {
        const grid3 = el.gridstack;
        if (opt)
          grid3.opts = { ...grid3.opts, ...opt };
        if (opt.children !== void 0)
          grid3.load(opt.children);
        return grid3;
      }
      const parentIsGrid = parent.classList.contains("grid-stack");
      if (!parentIsGrid || _GridStack.addRemoveCB) {
        if (_GridStack.addRemoveCB) {
          el = _GridStack.addRemoveCB(parent, opt, true, true);
        } else {
          el = Utils.createDiv(["grid-stack", opt.class], parent);
        }
      }
      const grid2 = _GridStack.init(opt, el);
      return grid2;
    }
    /** call this method to register your engine instead of the default one.
     * See instead `GridStackOptions.engineClass` if you only need to
     * replace just one instance.
     */
    static registerEngine(engineClass) {
      _GridStack.engineClass = engineClass;
    }
    /** @internal create placeholder DIV as needed */
    get placeholder() {
      if (!this._placeholder) {
        this._placeholder = Utils.createDiv([this.opts.placeholderClass, gridDefaults.itemClass, this.opts.itemClass]);
        const placeholderChild = Utils.createDiv(["placeholder-content"], this._placeholder);
        if (this.opts.placeholderText) {
          placeholderChild.textContent = this.opts.placeholderText;
        }
      }
      return this._placeholder;
    }
    /**
     * Construct a grid item from the given element and options
     * @param el the HTML element tied to this grid after it's been initialized
     * @param opts grid options - public for classes to access, but use methods to modify!
     */
    constructor(el, opts = {}) {
      this.el = el;
      this.opts = opts;
      this.animationDelay = 300 + 10;
      this._gsEventHandler = {};
      this._extraDragRow = 0;
      this.dragTransform = { xScale: 1, yScale: 1, xOffset: 0, yOffset: 0 };
      el.gridstack = this;
      this.opts = opts = opts || {};
      if (!el.classList.contains("grid-stack")) {
        this.el.classList.add("grid-stack");
      }
      if (opts.row) {
        opts.minRow = opts.maxRow = opts.row;
        delete opts.row;
      }
      const rowAttr = Utils.toNumber(el.getAttribute("gs-row"));
      if (opts.column === "auto") {
        delete opts.column;
      }
      if (opts.alwaysShowResizeHandle !== void 0) {
        opts._alwaysShowResizeHandle = opts.alwaysShowResizeHandle;
      }
      let bk = opts.columnOpts?.breakpoints;
      const oldOpts = opts;
      if (oldOpts.oneColumnModeDomSort) {
        delete oldOpts.oneColumnModeDomSort;
        console.log("warning: Gridstack oneColumnModeDomSort no longer supported. Use GridStackOptions.columnOpts instead.");
      }
      if (oldOpts.oneColumnSize || oldOpts.disableOneColumnMode === false) {
        const oneSize = oldOpts.oneColumnSize || 768;
        delete oldOpts.oneColumnSize;
        delete oldOpts.disableOneColumnMode;
        opts.columnOpts = opts.columnOpts || {};
        bk = opts.columnOpts.breakpoints = opts.columnOpts.breakpoints || [];
        let oneColumn = bk.find((b) => b.c === 1);
        if (!oneColumn) {
          oneColumn = { c: 1, w: oneSize };
          bk.push(oneColumn, { c: 12, w: oneSize + 1 });
        } else
          oneColumn.w = oneSize;
      }
      const resp = opts.columnOpts;
      if (resp) {
        if (!resp.columnWidth && !resp.breakpoints?.length) {
          delete opts.columnOpts;
          bk = void 0;
        } else {
          resp.columnMax = resp.columnMax || 12;
        }
      }
      if (bk?.length > 1)
        bk.sort((a, b) => (b.w || 0) - (a.w || 0));
      const defaults = {
        ...Utils.cloneDeep(gridDefaults),
        column: Utils.toNumber(el.getAttribute("gs-column")) || gridDefaults.column,
        minRow: rowAttr ? rowAttr : Utils.toNumber(el.getAttribute("gs-min-row")) || gridDefaults.minRow,
        maxRow: rowAttr ? rowAttr : Utils.toNumber(el.getAttribute("gs-max-row")) || gridDefaults.maxRow,
        staticGrid: Utils.toBool(el.getAttribute("gs-static")) || gridDefaults.staticGrid,
        sizeToContent: Utils.toBool(el.getAttribute("gs-size-to-content")) || void 0,
        draggable: {
          handle: (opts.handleClass ? "." + opts.handleClass : opts.handle ? opts.handle : "") || gridDefaults.draggable.handle
        },
        removableOptions: {
          accept: opts.itemClass || gridDefaults.removableOptions.accept,
          decline: gridDefaults.removableOptions.decline
        }
      };
      if (el.getAttribute("gs-animate")) {
        defaults.animate = Utils.toBool(el.getAttribute("gs-animate"));
      }
      opts = Utils.defaults(opts, defaults);
      this._initMargin();
      this.checkDynamicColumn();
      this.el.classList.add("gs-" + opts.column);
      if (opts.rtl === "auto") {
        opts.rtl = el.style.direction === "rtl";
      }
      if (opts.rtl) {
        this.el.classList.add("grid-stack-rtl");
      }
      const parentGridItem = this.el.closest("." + gridDefaults.itemClass);
      const parentNode = parentGridItem?.gridstackNode;
      if (parentNode) {
        parentNode.subGrid = this;
        this.parentGridNode = parentNode;
        this.el.classList.add("grid-stack-nested");
        parentNode.el.classList.add("grid-stack-sub-grid");
      }
      this._isAutoCellHeight = opts.cellHeight === "auto";
      if (this._isAutoCellHeight || opts.cellHeight === "initial") {
        this.cellHeight(void 0, false);
      } else {
        if (typeof opts.cellHeight == "number" && opts.cellHeightUnit && opts.cellHeightUnit !== gridDefaults.cellHeightUnit) {
          opts.cellHeight = opts.cellHeight + opts.cellHeightUnit;
          delete opts.cellHeightUnit;
        }
        this.cellHeight(opts.cellHeight, false);
      }
      if (opts.alwaysShowResizeHandle === "mobile") {
        opts.alwaysShowResizeHandle = isTouch;
      }
      this._styleSheetClass = "gs-id-" + GridStackEngine._idSeq++;
      this.el.classList.add(this._styleSheetClass);
      this._setStaticClass();
      const engineClass = opts.engineClass || _GridStack.engineClass || GridStackEngine;
      this.engine = new engineClass({
        column: this.getColumn(),
        float: opts.float,
        maxRow: opts.maxRow,
        onChange: (cbNodes) => {
          let maxH = 0;
          this.engine.nodes.forEach((n) => {
            maxH = Math.max(maxH, n.y + n.h);
          });
          cbNodes.forEach((n) => {
            const el2 = n.el;
            if (!el2)
              return;
            if (n._removeDOM) {
              if (el2)
                el2.remove();
              delete n._removeDOM;
            } else {
              this._writePosAttr(el2, n);
            }
          });
          this._updateStyles(false, maxH);
        }
      });
      this._updateStyles(false, 0);
      if (opts.auto) {
        this.batchUpdate();
        this.engine._loading = true;
        this.getGridItems().forEach((el2) => this._prepareElement(el2));
        delete this.engine._loading;
        this.batchUpdate(false);
      }
      if (opts.children) {
        const children = opts.children;
        delete opts.children;
        if (children.length)
          this.load(children);
      }
      this.setAnimation();
      if (opts.subGridDynamic && !DDManager.pauseDrag)
        DDManager.pauseDrag = true;
      if (opts.draggable?.pause !== void 0)
        DDManager.pauseDrag = opts.draggable.pause;
      this._setupRemoveDrop();
      this._setupAcceptWidget();
      this._updateResizeEvent();
    }
    /**
     * add a new widget and returns it.
     *
     * Widget will be always placed even if result height is more than actual grid height.
     * You need to use `willItFit()` before calling addWidget for additional check.
     * See also `makeWidget(el)` for DOM element.
     *
     * @example
     * const grid = GridStack.init();
     * grid.addWidget({w: 3, content: 'hello'});
     *
     * @param w GridStackWidget definition. used MakeWidget(el) if you have dom element instead.
     */
    addWidget(w) {
      if (typeof w === "string") {
        console.error("V11: GridStack.addWidget() does not support string anymore. see #2736");
        return;
      }
      if (w.ELEMENT_NODE) {
        console.error("V11: GridStack.addWidget() does not support HTMLElement anymore. use makeWidget()");
        return this.makeWidget(w);
      }
      let el;
      let node = w;
      node.grid = this;
      if (node?.el) {
        el = node.el;
      } else if (_GridStack.addRemoveCB) {
        el = _GridStack.addRemoveCB(this.el, w, true, false);
      } else {
        el = this.createWidgetDivs(node);
      }
      if (!el)
        return;
      node = el.gridstackNode;
      if (node && el.parentElement === this.el && this.engine.nodes.find((n) => n._id === node._id))
        return el;
      const domAttr = this._readAttr(el);
      Utils.defaults(w, domAttr);
      this.engine.prepareNode(w);
      this.el.appendChild(el);
      this.makeWidget(el, w);
      return el;
    }
    /** create the default grid item divs, and content (possibly lazy loaded) by using GridStack.renderCB() */
    createWidgetDivs(n) {
      const el = Utils.createDiv(["grid-stack-item", this.opts.itemClass]);
      const cont = Utils.createDiv(["grid-stack-item-content"], el);
      if (Utils.lazyLoad(n)) {
        if (!n.visibleObservable) {
          n.visibleObservable = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) {
              n.visibleObservable?.disconnect();
              delete n.visibleObservable;
              _GridStack.renderCB(cont, n);
              n.grid?.prepareDragDrop(n.el);
            }
          });
          window.setTimeout(() => n.visibleObservable?.observe(el));
        }
      } else
        _GridStack.renderCB(cont, n);
      return el;
    }
    /**
     * Convert an existing gridItem element into a sub-grid with the given (optional) options, else inherit them
     * from the parent's subGrid options.
     * @param el gridItem element to convert
     * @param ops (optional) sub-grid options, else default to node, then parent settings, else defaults
     * @param nodeToAdd (optional) node to add to the newly created sub grid (used when dragging over existing regular item)
     * @param saveContent if true (default) the html inside .grid-stack-content will be saved to child widget
     * @returns newly created grid
     */
    makeSubGrid(el, ops, nodeToAdd, saveContent = true) {
      let node = el.gridstackNode;
      if (!node) {
        node = this.makeWidget(el).gridstackNode;
      }
      if (node.subGrid?.el)
        return node.subGrid;
      let subGridTemplate;
      let grid2 = this;
      while (grid2 && !subGridTemplate) {
        subGridTemplate = grid2.opts?.subGridOpts;
        grid2 = grid2.parentGridNode?.grid;
      }
      ops = Utils.cloneDeep({
        // by default sub-grid inherit from us | parent, other than id, children, etc...
        ...this.opts,
        id: void 0,
        children: void 0,
        column: "auto",
        columnOpts: void 0,
        layout: "list",
        subGridOpts: void 0,
        ...subGridTemplate || {},
        ...ops || node.subGridOpts || {}
      });
      node.subGridOpts = ops;
      let autoColumn;
      if (ops.column === "auto") {
        autoColumn = true;
        ops.column = Math.max(node.w || 1, nodeToAdd?.w || 1);
        delete ops.columnOpts;
      }
      let content = node.el.querySelector(".grid-stack-item-content");
      let newItem;
      let newItemOpt;
      if (saveContent) {
        this._removeDD(node.el);
        newItemOpt = { ...node, x: 0, y: 0 };
        Utils.removeInternalForSave(newItemOpt);
        delete newItemOpt.subGridOpts;
        if (node.content) {
          newItemOpt.content = node.content;
          delete node.content;
        }
        if (_GridStack.addRemoveCB) {
          newItem = _GridStack.addRemoveCB(this.el, newItemOpt, true, false);
        } else {
          newItem = Utils.createDiv(["grid-stack-item"]);
          newItem.appendChild(content);
          content = Utils.createDiv(["grid-stack-item-content"], node.el);
        }
        this.prepareDragDrop(node.el);
      }
      if (nodeToAdd) {
        const w = autoColumn ? ops.column : node.w;
        const h = node.h + nodeToAdd.h;
        const style = node.el.style;
        style.transition = "none";
        this.update(node.el, { w, h });
        setTimeout(() => style.transition = null);
      }
      const subGrid = node.subGrid = _GridStack.addGrid(content, ops);
      if (nodeToAdd?._moving)
        subGrid._isTemp = true;
      if (autoColumn)
        subGrid._autoColumn = true;
      if (saveContent) {
        subGrid.makeWidget(newItem, newItemOpt);
      }
      if (nodeToAdd) {
        if (nodeToAdd._moving) {
          window.setTimeout(() => Utils.simulateMouseEvent(nodeToAdd._event, "mouseenter", subGrid.el), 0);
        } else {
          subGrid.makeWidget(node.el, node);
        }
      }
      this.resizeToContentCheck(false, node);
      return subGrid;
    }
    /**
     * called when an item was converted into a nested grid to accommodate a dragged over item, but then item leaves - return back
     * to the original grid-item. Also called to remove empty sub-grids when last item is dragged out (since re-creating is simple)
     */
    removeAsSubGrid(nodeThatRemoved) {
      const pGrid = this.parentGridNode?.grid;
      if (!pGrid)
        return;
      pGrid.batchUpdate();
      pGrid.removeWidget(this.parentGridNode.el, true, true);
      this.engine.nodes.forEach((n) => {
        n.x += this.parentGridNode.x;
        n.y += this.parentGridNode.y;
        pGrid.makeWidget(n.el, n);
      });
      pGrid.batchUpdate(false);
      if (this.parentGridNode)
        delete this.parentGridNode.subGrid;
      delete this.parentGridNode;
      if (nodeThatRemoved) {
        window.setTimeout(() => Utils.simulateMouseEvent(nodeThatRemoved._event, "mouseenter", pGrid.el), 0);
      }
    }
    /**
     * saves the current layout returning a list of widgets for serialization which might include any nested grids.
     * @param saveContent if true (default) the latest html inside .grid-stack-content will be saved to GridStackWidget.content field, else it will
     * be removed.
     * @param saveGridOpt if true (default false), save the grid options itself, so you can call the new GridStack.addGrid()
     * to recreate everything from scratch. GridStackOptions.children would then contain the widget list instead.
     * @param saveCB callback for each node -> widget, so application can insert additional data to be saved into the widget data structure.
     * @returns list of widgets or full grid option, including .children list of widgets
     */
    save(saveContent = true, saveGridOpt = false, saveCB = _GridStack.saveCB) {
      const list = this.engine.save(saveContent, saveCB);
      list.forEach((n) => {
        if (saveContent && n.el && !n.subGrid && !saveCB) {
          const itemContent = n.el.querySelector(".grid-stack-item-content");
          n.content = itemContent?.innerHTML;
          if (!n.content)
            delete n.content;
        } else {
          if (!saveContent && !saveCB) {
            delete n.content;
          }
          if (n.subGrid?.el) {
            const listOrOpt = n.subGrid.save(saveContent, saveGridOpt, saveCB);
            n.subGridOpts = saveGridOpt ? listOrOpt : { children: listOrOpt };
            delete n.subGrid;
          }
        }
        delete n.el;
      });
      if (saveGridOpt) {
        const o = Utils.cloneDeep(this.opts);
        if (o.marginBottom === o.marginTop && o.marginRight === o.marginLeft && o.marginTop === o.marginRight) {
          o.margin = o.marginTop;
          delete o.marginTop;
          delete o.marginRight;
          delete o.marginBottom;
          delete o.marginLeft;
        }
        if (o.rtl === (this.el.style.direction === "rtl")) {
          o.rtl = "auto";
        }
        if (this._isAutoCellHeight) {
          o.cellHeight = "auto";
        }
        if (this._autoColumn) {
          o.column = "auto";
        }
        const origShow = o._alwaysShowResizeHandle;
        delete o._alwaysShowResizeHandle;
        if (origShow !== void 0) {
          o.alwaysShowResizeHandle = origShow;
        } else {
          delete o.alwaysShowResizeHandle;
        }
        Utils.removeInternalAndSame(o, gridDefaults);
        o.children = list;
        return o;
      }
      return list;
    }
    /**
     * load the widgets from a list. This will call update() on each (matching by id) or add/remove widgets that are not there.
     *
     * @param items list of widgets definition to update/create
     * @param addRemove boolean (default true) or callback method can be passed to control if and how missing widgets can be added/removed, giving
     * the user control of insertion.
     *
     * @example
     * see http://gridstackjs.com/demo/serialization.html
     */
    load(items, addRemove = _GridStack.addRemoveCB || true) {
      items = Utils.cloneDeep(items);
      const column = this.getColumn();
      items.forEach((n) => {
        n.w = n.w || 1;
        n.h = n.h || 1;
      });
      items = Utils.sort(items);
      this.engine.skipCacheUpdate = this._ignoreLayoutsNodeChange = true;
      let maxColumn = 0;
      items.forEach((n) => {
        maxColumn = Math.max(maxColumn, (n.x || 0) + n.w);
      });
      if (maxColumn > this.engine.defaultColumn)
        this.engine.defaultColumn = maxColumn;
      if (maxColumn > column)
        this.engine.cacheLayout(items, maxColumn, true);
      const prevCB = _GridStack.addRemoveCB;
      if (typeof addRemove === "function")
        _GridStack.addRemoveCB = addRemove;
      const removed = [];
      this.batchUpdate();
      const blank = !this.engine.nodes.length;
      if (blank)
        this.setAnimation(false);
      if (!blank && addRemove) {
        const copyNodes = [...this.engine.nodes];
        copyNodes.forEach((n) => {
          if (!n.id)
            return;
          const item = Utils.find(items, n.id);
          if (!item) {
            if (_GridStack.addRemoveCB)
              _GridStack.addRemoveCB(this.el, n, false, false);
            removed.push(n);
            this.removeWidget(n.el, true, false);
          }
        });
      }
      this.engine._loading = true;
      const updateNodes = [];
      this.engine.nodes = this.engine.nodes.filter((n) => {
        if (Utils.find(items, n.id)) {
          updateNodes.push(n);
          return false;
        }
        return true;
      });
      items.forEach((w) => {
        const item = Utils.find(updateNodes, w.id);
        if (item) {
          if (Utils.shouldSizeToContent(item))
            w.h = item.h;
          this.engine.nodeBoundFix(w);
          if (w.autoPosition || w.x === void 0 || w.y === void 0) {
            w.w = w.w || item.w;
            w.h = w.h || item.h;
            this.engine.findEmptyPosition(w);
          }
          this.engine.nodes.push(item);
          if (Utils.samePos(item, w) && this.engine.nodes.length > 1) {
            this.moveNode(item, { ...w, forceCollide: true });
            Utils.copyPos(w, item);
          }
          this.update(item.el, w);
          if (w.subGridOpts?.children) {
            const sub = item.el.querySelector(".grid-stack");
            if (sub && sub.gridstack) {
              sub.gridstack.load(w.subGridOpts.children);
            }
          }
        } else if (addRemove) {
          this.addWidget(w);
        }
      });
      delete this.engine._loading;
      this.engine.removedNodes = removed;
      this.batchUpdate(false);
      delete this._ignoreLayoutsNodeChange;
      delete this.engine.skipCacheUpdate;
      prevCB ? _GridStack.addRemoveCB = prevCB : delete _GridStack.addRemoveCB;
      if (blank && this.opts?.animate)
        this.setAnimation(this.opts.animate, true);
      return this;
    }
    /**
     * use before calling a bunch of `addWidget()` to prevent un-necessary relayouts in between (more efficient)
     * and get a single event callback. You will see no changes until `batchUpdate(false)` is called.
     */
    batchUpdate(flag = true) {
      this.engine.batchUpdate(flag);
      if (!flag) {
        this._updateContainerHeight();
        this._triggerRemoveEvent();
        this._triggerAddEvent();
        this._triggerChangeEvent();
      }
      return this;
    }
    /**
     * Gets current cell height.
     */
    getCellHeight(forcePixel = false) {
      if (this.opts.cellHeight && this.opts.cellHeight !== "auto" && (!forcePixel || !this.opts.cellHeightUnit || this.opts.cellHeightUnit === "px")) {
        return this.opts.cellHeight;
      }
      if (this.opts.cellHeightUnit === "rem") {
        return this.opts.cellHeight * parseFloat(getComputedStyle(document.documentElement).fontSize);
      }
      if (this.opts.cellHeightUnit === "em") {
        return this.opts.cellHeight * parseFloat(getComputedStyle(this.el).fontSize);
      }
      if (this.opts.cellHeightUnit === "cm") {
        return this.opts.cellHeight * (96 / 2.54);
      }
      if (this.opts.cellHeightUnit === "mm") {
        return this.opts.cellHeight * (96 / 2.54) / 10;
      }
      const el = this.el.querySelector("." + this.opts.itemClass);
      if (el) {
        const h = Utils.toNumber(el.getAttribute("gs-h")) || 1;
        return Math.round(el.offsetHeight / h);
      }
      const rows = parseInt(this.el.getAttribute("gs-current-row"));
      return rows ? Math.round(this.el.getBoundingClientRect().height / rows) : this.opts.cellHeight;
    }
    /**
     * Update current cell height - see `GridStackOptions.cellHeight` for format.
     * This method rebuilds an internal CSS style sheet.
     * Note: You can expect performance issues if call this method too often.
     *
     * @param val the cell height. If not passed (undefined), cells content will be made square (match width minus margin),
     * if pass 0 the CSS will be generated by the application instead.
     * @param update (Optional) if false, styles will not be updated
     *
     * @example
     * grid.cellHeight(100); // same as 100px
     * grid.cellHeight('70px');
     * grid.cellHeight(grid.cellWidth() * 1.2);
     */
    cellHeight(val, update = true) {
      if (update && val !== void 0) {
        if (this._isAutoCellHeight !== (val === "auto")) {
          this._isAutoCellHeight = val === "auto";
          this._updateResizeEvent();
        }
      }
      if (val === "initial" || val === "auto") {
        val = void 0;
      }
      if (val === void 0) {
        const marginDiff = -this.opts.marginRight - this.opts.marginLeft + this.opts.marginTop + this.opts.marginBottom;
        val = this.cellWidth() + marginDiff;
      }
      const data = Utils.parseHeight(val);
      if (this.opts.cellHeightUnit === data.unit && this.opts.cellHeight === data.h) {
        return this;
      }
      this.opts.cellHeightUnit = data.unit;
      this.opts.cellHeight = data.h;
      this.resizeToContentCheck();
      if (update) {
        this._updateStyles(true);
      }
      return this;
    }
    /** Gets current cell width. */
    cellWidth() {
      return this._widthOrContainer() / this.getColumn();
    }
    /** return our expected width (or parent) , and optionally of window for dynamic column check */
    _widthOrContainer(forBreakpoint = false) {
      return forBreakpoint && this.opts.columnOpts?.breakpointForWindow ? window.innerWidth : this.el.clientWidth || this.el.parentElement.clientWidth || window.innerWidth;
    }
    /** checks for dynamic column count for our current size, returning true if changed */
    checkDynamicColumn() {
      const resp = this.opts.columnOpts;
      if (!resp || !resp.columnWidth && !resp.breakpoints?.length)
        return false;
      const column = this.getColumn();
      let newColumn = column;
      const w = this._widthOrContainer(true);
      if (resp.columnWidth) {
        newColumn = Math.min(Math.round(w / resp.columnWidth) || 1, resp.columnMax);
      } else {
        newColumn = resp.columnMax;
        let i = 0;
        while (i < resp.breakpoints.length && w <= resp.breakpoints[i].w) {
          newColumn = resp.breakpoints[i++].c || column;
        }
      }
      if (newColumn !== column) {
        const bk = resp.breakpoints?.find((b) => b.c === newColumn);
        this.column(newColumn, bk?.layout || resp.layout);
        return true;
      }
      return false;
    }
    /**
     * re-layout grid items to reclaim any empty space. Options are:
     * 'list' keep the widget left->right order the same, even if that means leaving an empty slot if things don't fit
     * 'compact' might re-order items to fill any empty space
     *
     * doSort - 'false' to let you do your own sorting ahead in case you need to control a different order. (default to sort)
     */
    compact(layout = "compact", doSort = true) {
      this.engine.compact(layout, doSort);
      this._triggerChangeEvent();
      return this;
    }
    /**
     * set the number of columns in the grid. Will update existing widgets to conform to new number of columns,
     * as well as cache the original layout so you can revert back to previous positions without loss.
     * Requires `gridstack-extra.css` or `gridstack-extra.min.css` for [2-11],
     * else you will need to generate correct CSS (see https://github.com/gridstack/gridstack.js#change-grid-columns)
     * @param column - Integer > 0 (default 12).
     * @param layout specify the type of re-layout that will happen (position, size, etc...).
     * Note: items will never be outside of the current column boundaries. default ('moveScale'). Ignored for 1 column
     */
    column(column, layout = "moveScale") {
      if (!column || column < 1 || this.opts.column === column)
        return this;
      const oldColumn = this.getColumn();
      this.opts.column = column;
      if (!this.engine)
        return this;
      this.engine.column = column;
      this.el.classList.remove("gs-" + oldColumn);
      this.el.classList.add("gs-" + column);
      this.engine.columnChanged(oldColumn, column, layout);
      if (this._isAutoCellHeight)
        this.cellHeight();
      this.resizeToContentCheck(true);
      this._ignoreLayoutsNodeChange = true;
      this._triggerChangeEvent();
      delete this._ignoreLayoutsNodeChange;
      return this;
    }
    /**
     * get the number of columns in the grid (default 12)
     */
    getColumn() {
      return this.opts.column;
    }
    /** returns an array of grid HTML elements (no placeholder) - used to iterate through our children in DOM order */
    getGridItems() {
      return Array.from(this.el.children).filter((el) => el.matches("." + this.opts.itemClass) && !el.matches("." + this.opts.placeholderClass));
    }
    /** true if changeCB should be ignored due to column change, sizeToContent, loading, etc... which caller can ignore for dirty flag case */
    isIgnoreChangeCB() {
      return this._ignoreLayoutsNodeChange;
    }
    /**
     * Destroys a grid instance. DO NOT CALL any methods or access any vars after this as it will free up members.
     * @param removeDOM if `false` grid and items HTML elements will not be removed from the DOM (Optional. Default `true`).
     */
    destroy(removeDOM = true) {
      if (!this.el)
        return;
      this.offAll();
      this._updateResizeEvent(true);
      this.setStatic(true, false);
      this.setAnimation(false);
      if (!removeDOM) {
        this.removeAll(removeDOM);
        this.el.classList.remove(this._styleSheetClass);
        this.el.removeAttribute("gs-current-row");
      } else {
        this.el.parentNode.removeChild(this.el);
      }
      this._removeStylesheet();
      delete this.parentGridNode?.subGrid;
      delete this.parentGridNode;
      delete this.opts;
      delete this._placeholder?.gridstackNode;
      delete this._placeholder;
      delete this.engine;
      delete this.el.gridstack;
      delete this.el;
      return this;
    }
    /**
     * enable/disable floating widgets (default: `false`) See [example](http://gridstackjs.com/demo/float.html)
     */
    float(val) {
      if (this.opts.float !== val) {
        this.opts.float = this.engine.float = val;
        this._triggerChangeEvent();
      }
      return this;
    }
    /**
     * get the current float mode
     */
    getFloat() {
      return this.engine.float;
    }
    /**
     * Get the position of the cell under a pixel on screen.
     * @param position the position of the pixel to resolve in
     * absolute coordinates, as an object with top and left properties
     * @param useDocRelative if true, value will be based on document position vs parent position (Optional. Default false).
     * Useful when grid is within `position: relative` element
     *
     * Returns an object with properties `x` and `y` i.e. the column and row in the grid.
     */
    getCellFromPixel(position, useDocRelative = false) {
      const box = this.el.getBoundingClientRect();
      let containerPos;
      if (useDocRelative) {
        containerPos = { top: box.top + document.documentElement.scrollTop, left: box.left };
      } else {
        containerPos = { top: this.el.offsetTop, left: this.el.offsetLeft };
      }
      const relativeLeft = position.left - containerPos.left;
      const relativeTop = position.top - containerPos.top;
      const columnWidth = box.width / this.getColumn();
      const rowHeight = box.height / parseInt(this.el.getAttribute("gs-current-row"));
      return { x: Math.floor(relativeLeft / columnWidth), y: Math.floor(relativeTop / rowHeight) };
    }
    /** returns the current number of rows, which will be at least `minRow` if set */
    getRow() {
      return Math.max(this.engine.getRow(), this.opts.minRow);
    }
    /**
     * Checks if specified area is empty.
     * @param x the position x.
     * @param y the position y.
     * @param w the width of to check
     * @param h the height of to check
     */
    isAreaEmpty(x, y, w, h) {
      return this.engine.isAreaEmpty(x, y, w, h);
    }
    /**
     * If you add elements to your grid by hand (or have some framework creating DOM), you have to tell gridstack afterwards to make them widgets.
     * If you want gridstack to add the elements for you, use `addWidget()` instead.
     * Makes the given element a widget and returns it.
     * @param els widget or single selector to convert.
     * @param options widget definition to use instead of reading attributes or using default sizing values
     *
     * @example
     * const grid = GridStack.init();
     * grid.el.innerHtml = '<div id="1" gs-w="3"></div><div id="2"></div>';
     * grid.makeWidget('1');
     * grid.makeWidget('2', {w:2, content: 'hello'});
     */
    makeWidget(els, options) {
      const el = _GridStack.getElement(els);
      if (!el)
        return;
      if (!el.parentElement)
        this.el.appendChild(el);
      this._prepareElement(el, true, options);
      const node = el.gridstackNode;
      this._updateContainerHeight();
      if (node.subGridOpts) {
        this.makeSubGrid(el, node.subGridOpts, void 0, false);
      }
      let resetIgnoreLayoutsNodeChange;
      if (this.opts.column === 1 && !this._ignoreLayoutsNodeChange) {
        resetIgnoreLayoutsNodeChange = this._ignoreLayoutsNodeChange = true;
      }
      this._triggerAddEvent();
      this._triggerChangeEvent();
      if (resetIgnoreLayoutsNodeChange)
        delete this._ignoreLayoutsNodeChange;
      return el;
    }
    on(name, callback) {
      if (name.indexOf(" ") !== -1) {
        const names = name.split(" ");
        names.forEach((name2) => this.on(name2, callback));
        return this;
      }
      if (name === "change" || name === "added" || name === "removed" || name === "enable" || name === "disable") {
        const noData = name === "enable" || name === "disable";
        if (noData) {
          this._gsEventHandler[name] = (event) => callback(event);
        } else {
          this._gsEventHandler[name] = (event) => {
            if (event.detail)
              callback(event, event.detail);
          };
        }
        this.el.addEventListener(name, this._gsEventHandler[name]);
      } else if (name === "drag" || name === "dragstart" || name === "dragstop" || name === "resizestart" || name === "resize" || name === "resizestop" || name === "dropped" || name === "resizecontent") {
        this._gsEventHandler[name] = callback;
      } else {
        console.error("GridStack.on(" + name + ") event not supported");
      }
      return this;
    }
    /**
     * unsubscribe from the 'on' event GridStackEvent
     * @param name of the event (see possible values) or list of names space separated
     */
    off(name) {
      if (name.indexOf(" ") !== -1) {
        const names = name.split(" ");
        names.forEach((name2) => this.off(name2));
        return this;
      }
      if (name === "change" || name === "added" || name === "removed" || name === "enable" || name === "disable") {
        if (this._gsEventHandler[name]) {
          this.el.removeEventListener(name, this._gsEventHandler[name]);
        }
      }
      delete this._gsEventHandler[name];
      return this;
    }
    /** remove all event handlers */
    offAll() {
      Object.keys(this._gsEventHandler).forEach((key) => this.off(key));
      return this;
    }
    /**
     * Removes widget from the grid.
     * @param el  widget or selector to modify
     * @param removeDOM if `false` DOM element won't be removed from the tree (Default? true).
     * @param triggerEvent if `false` (quiet mode) element will not be added to removed list and no 'removed' callbacks will be called (Default? true).
     */
    removeWidget(els, removeDOM = true, triggerEvent = true) {
      if (!els) {
        console.error("Error: GridStack.removeWidget(undefined) called");
        return this;
      }
      _GridStack.getElements(els).forEach((el) => {
        if (el.parentElement && el.parentElement !== this.el)
          return;
        let node = el.gridstackNode;
        if (!node) {
          node = this.engine.nodes.find((n) => el === n.el);
        }
        if (!node)
          return;
        if (removeDOM && _GridStack.addRemoveCB) {
          _GridStack.addRemoveCB(this.el, node, false, false);
        }
        delete el.gridstackNode;
        this._removeDD(el);
        this.engine.removeNode(node, removeDOM, triggerEvent);
        if (removeDOM && el.parentElement) {
          el.remove();
        }
      });
      if (triggerEvent) {
        this._triggerRemoveEvent();
        this._triggerChangeEvent();
      }
      return this;
    }
    /**
     * Removes all widgets from the grid.
     * @param removeDOM if `false` DOM elements won't be removed from the tree (Default? `true`).
     * @param triggerEvent if `false` (quiet mode) element will not be added to removed list and no 'removed' callbacks will be called (Default? true).
     */
    removeAll(removeDOM = true, triggerEvent = true) {
      this.engine.nodes.forEach((n) => {
        if (removeDOM && _GridStack.addRemoveCB) {
          _GridStack.addRemoveCB(this.el, n, false, false);
        }
        delete n.el.gridstackNode;
        if (!this.opts.staticGrid)
          this._removeDD(n.el);
      });
      this.engine.removeAll(removeDOM, triggerEvent);
      if (triggerEvent)
        this._triggerRemoveEvent();
      return this;
    }
    /**
     * Toggle the grid animation state.  Toggles the `grid-stack-animate` class.
     * @param doAnimate if true the grid will animate.
     * @param delay if true setting will be set on next event loop.
     */
    setAnimation(doAnimate = this.opts.animate, delay) {
      if (delay) {
        setTimeout(() => {
          if (this.opts)
            this.setAnimation(doAnimate);
        });
      } else if (doAnimate) {
        this.el.classList.add("grid-stack-animate");
      } else {
        this.el.classList.remove("grid-stack-animate");
      }
      return this;
    }
    /** @internal */
    hasAnimationCSS() {
      return this.el.classList.contains("grid-stack-animate");
    }
    /**
     * Toggle the grid static state, which permanently removes/add Drag&Drop support, unlike disable()/enable() that just turns it off/on.
     * Also toggle the grid-stack-static class.
     * @param val if true the grid become static.
     * @param updateClass true (default) if css class gets updated
     * @param recurse true (default) if sub-grids also get updated
     */
    setStatic(val, updateClass = true, recurse = true) {
      if (!!this.opts.staticGrid === val)
        return this;
      val ? this.opts.staticGrid = true : delete this.opts.staticGrid;
      this._setupRemoveDrop();
      this._setupAcceptWidget();
      this.engine.nodes.forEach((n) => {
        this.prepareDragDrop(n.el);
        if (n.subGrid && recurse)
          n.subGrid.setStatic(val, updateClass, recurse);
      });
      if (updateClass) {
        this._setStaticClass();
      }
      return this;
    }
    /**
     * Updates the passed in options on the grid (similar to update(widget) for for the grid options).
     * @param options PARTIAL grid options to update - only items specified will be updated.
     * NOTE: not all options updating are currently supported (lot of code, unlikely to change)
     */
    updateOptions(o) {
      const opts = this.opts;
      if (o.acceptWidgets !== void 0)
        this._setupAcceptWidget();
      if (o.animate !== void 0)
        this.setAnimation();
      if (o.cellHeight) {
        this.cellHeight(o.cellHeight, true);
        delete o.cellHeight;
      }
      if (o.class && o.class !== opts.class) {
        if (opts.class)
          this.el.classList.remove(opts.class);
        this.el.classList.add(o.class);
      }
      if (typeof o.column === "number" && !o.columnOpts) {
        this.column(o.column);
        delete o.column;
      }
      if (o.margin !== void 0)
        this.margin(o.margin);
      if (o.staticGrid !== void 0)
        this.setStatic(o.staticGrid);
      if (o.disableDrag !== void 0 && !o.staticGrid)
        this.enableMove(!o.disableDrag);
      if (o.disableResize !== void 0 && !o.staticGrid)
        this.enableResize(!o.disableResize);
      if (o.float !== void 0)
        this.float(o.float);
      if (o.row !== void 0) {
        opts.minRow = opts.maxRow = o.row;
      }
      if (o.children?.length) {
        this.load(o.children);
        delete o.children;
      }
      this.opts = { ...this.opts, ...o };
      return this;
    }
    /**
     * Updates widget position/size and other info. Note: if you need to call this on all nodes, use load() instead which will update what changed.
     * @param els  widget or selector of objects to modify (note: setting the same x,y for multiple items will be indeterministic and likely unwanted)
     * @param opt new widget options (x,y,w,h, etc..). Only those set will be updated.
     */
    update(els, opt) {
      _GridStack.getElements(els).forEach((el) => {
        const n = el?.gridstackNode;
        if (!n)
          return;
        const w = { ...Utils.copyPos({}, n), ...Utils.cloneDeep(opt) };
        this.engine.nodeBoundFix(w);
        delete w.autoPosition;
        const keys = ["x", "y", "w", "h"];
        let m;
        if (keys.some((k) => w[k] !== void 0 && w[k] !== n[k])) {
          m = {};
          keys.forEach((k) => {
            m[k] = w[k] !== void 0 ? w[k] : n[k];
            delete w[k];
          });
        }
        if (!m && (w.minW || w.minH || w.maxW || w.maxH)) {
          m = {};
        }
        if (w.content !== void 0) {
          const itemContent = el.querySelector(".grid-stack-item-content");
          if (itemContent && itemContent.textContent !== w.content) {
            n.content = w.content;
            _GridStack.renderCB(itemContent, w);
            if (n.subGrid?.el) {
              itemContent.appendChild(n.subGrid.el);
              if (!n.subGrid.opts.styleInHead)
                n.subGrid._updateStyles(true);
            }
          }
          delete w.content;
        }
        let changed = false;
        let ddChanged = false;
        for (const key in w) {
          if (key[0] !== "_" && n[key] !== w[key]) {
            n[key] = w[key];
            changed = true;
            ddChanged = ddChanged || !this.opts.staticGrid && (key === "noResize" || key === "noMove" || key === "locked");
          }
        }
        Utils.sanitizeMinMax(n);
        if (m) {
          const widthChanged = m.w !== void 0 && m.w !== n.w;
          this.moveNode(n, m);
          if (widthChanged && n.subGrid) {
            n.subGrid.onResize(this.hasAnimationCSS() ? n.w : void 0);
          } else {
            this.resizeToContentCheck(widthChanged, n);
          }
          delete n._orig;
        }
        if (m || changed) {
          this._writeAttr(el, n);
        }
        if (ddChanged) {
          this.prepareDragDrop(n.el);
        }
      });
      return this;
    }
    moveNode(n, m) {
      const wasUpdating = n._updating;
      if (!wasUpdating)
        this.engine.cleanNodes().beginUpdate(n);
      this.engine.moveNode(n, m);
      this._updateContainerHeight();
      if (!wasUpdating) {
        this._triggerChangeEvent();
        this.engine.endUpdate();
      }
    }
    /**
     * Updates widget height to match the content height to avoid v-scrollbar or dead space.
     * Note: this assumes only 1 child under resizeToContentParent='.grid-stack-item-content' (sized to gridItem minus padding) that is at the entire content size wanted.
     * @param el grid item element
     * @param useNodeH set to true if GridStackNode.h should be used instead of actual container height when we don't need to wait for animation to finish to get actual DOM heights
     */
    resizeToContent(el) {
      if (!el)
        return;
      el.classList.remove("size-to-content-max");
      if (!el.clientHeight)
        return;
      const n = el.gridstackNode;
      if (!n)
        return;
      const grid2 = n.grid;
      if (!grid2 || el.parentElement !== grid2.el)
        return;
      const cell = grid2.getCellHeight(true);
      if (!cell)
        return;
      let height = n.h ? n.h * cell : el.clientHeight;
      let item;
      if (n.resizeToContentParent)
        item = el.querySelector(n.resizeToContentParent);
      if (!item)
        item = el.querySelector(_GridStack.resizeToContentParent);
      if (!item)
        return;
      const padding = el.clientHeight - item.clientHeight;
      const itemH = n.h ? n.h * cell - padding : item.clientHeight;
      let wantedH;
      if (n.subGrid) {
        wantedH = n.subGrid.getRow() * n.subGrid.getCellHeight(true);
        const subRec = n.subGrid.el.getBoundingClientRect();
        const parentRec = n.subGrid.el.parentElement.getBoundingClientRect();
        wantedH += subRec.top - parentRec.top;
      } else if (n.subGridOpts?.children?.length) {
        return;
      } else {
        const child = item.firstElementChild;
        if (!child) {
          console.error(`Error: GridStack.resizeToContent() widget id:${n.id} '${_GridStack.resizeToContentParent}'.firstElementChild is null, make sure to have a div like container. Skipping sizing.`);
          return;
        }
        wantedH = child.getBoundingClientRect().height || itemH;
      }
      if (itemH === wantedH)
        return;
      height += wantedH - itemH;
      let h = Math.ceil(height / cell);
      const softMax = Number.isInteger(n.sizeToContent) ? n.sizeToContent : 0;
      if (softMax && h > softMax) {
        h = softMax;
        el.classList.add("size-to-content-max");
      }
      if (n.minH && h < n.minH)
        h = n.minH;
      else if (n.maxH && h > n.maxH)
        h = n.maxH;
      if (h !== n.h) {
        grid2._ignoreLayoutsNodeChange = true;
        grid2.moveNode(n, { h });
        delete grid2._ignoreLayoutsNodeChange;
      }
    }
    /** call the user resize (so they can do extra work) else our build in version */
    resizeToContentCBCheck(el) {
      if (_GridStack.resizeToContentCB)
        _GridStack.resizeToContentCB(el);
      else
        this.resizeToContent(el);
    }
    /** rotate (by swapping w & h) the passed in node - called when user press 'r' during dragging
     * @param els  widget or selector of objects to modify
     * @param relative optional pixel coord relative to upper/left corner to rotate around (will keep that cell under cursor)
     */
    rotate(els, relative) {
      _GridStack.getElements(els).forEach((el) => {
        const n = el.gridstackNode;
        if (!Utils.canBeRotated(n))
          return;
        const rot = { w: n.h, h: n.w, minH: n.minW, minW: n.minH, maxH: n.maxW, maxW: n.maxH };
        if (relative) {
          const pivotX = relative.left > 0 ? Math.floor(relative.left / this.cellWidth()) : 0;
          const pivotY = relative.top > 0 ? Math.floor(relative.top / this.opts.cellHeight) : 0;
          rot.x = n.x + pivotX - (n.h - (pivotY + 1));
          rot.y = n.y + pivotY - pivotX;
        }
        Object.keys(rot).forEach((k) => {
          if (rot[k] === void 0)
            delete rot[k];
        });
        const _orig = n._orig;
        this.update(el, rot);
        n._orig = _orig;
      });
      return this;
    }
    /**
     * Updates the margins which will set all 4 sides at once - see `GridStackOptions.margin` for format options (CSS string format of 1,2,4 values or single number).
     * @param value margin value
     */
    margin(value) {
      const isMultiValue = typeof value === "string" && value.split(" ").length > 1;
      if (!isMultiValue) {
        const data = Utils.parseHeight(value);
        if (this.opts.marginUnit === data.unit && this.opts.margin === data.h)
          return;
      }
      this.opts.margin = value;
      this.opts.marginTop = this.opts.marginBottom = this.opts.marginLeft = this.opts.marginRight = void 0;
      this._initMargin();
      this._updateStyles(true);
      return this;
    }
    /** returns current margin number value (undefined if 4 sides don't match) */
    getMargin() {
      return this.opts.margin;
    }
    /**
     * Returns true if the height of the grid will be less than the vertical
     * constraint. Always returns true if grid doesn't have height constraint.
     * @param node contains x,y,w,h,auto-position options
     *
     * @example
     * if (grid.willItFit(newWidget)) {
     *   grid.addWidget(newWidget);
     * } else {
     *   alert('Not enough free space to place the widget');
     * }
     */
    willItFit(node) {
      if (arguments.length > 1) {
        console.warn("gridstack.ts: `willItFit(x,y,w,h,autoPosition)` is deprecated. Use `willItFit({x, y,...})`. It will be removed soon");
        const a = arguments;
        let i = 0, w = { x: a[i++], y: a[i++], w: a[i++], h: a[i++], autoPosition: a[i++] };
        return this.willItFit(w);
      }
      return this.engine.willItFit(node);
    }
    /** @internal */
    _triggerChangeEvent() {
      if (this.engine.batchMode)
        return this;
      const elements = this.engine.getDirtyNodes(true);
      if (elements && elements.length) {
        if (!this._ignoreLayoutsNodeChange) {
          this.engine.layoutsNodesChange(elements);
        }
        this._triggerEvent("change", elements);
      }
      this.engine.saveInitial();
      return this;
    }
    /** @internal */
    _triggerAddEvent() {
      if (this.engine.batchMode)
        return this;
      if (this.engine.addedNodes?.length) {
        if (!this._ignoreLayoutsNodeChange) {
          this.engine.layoutsNodesChange(this.engine.addedNodes);
        }
        this.engine.addedNodes.forEach((n) => {
          delete n._dirty;
        });
        const addedNodes = [...this.engine.addedNodes];
        this.engine.addedNodes = [];
        this._triggerEvent("added", addedNodes);
      }
      return this;
    }
    /** @internal */
    _triggerRemoveEvent() {
      if (this.engine.batchMode)
        return this;
      if (this.engine.removedNodes?.length) {
        const removedNodes = [...this.engine.removedNodes];
        this.engine.removedNodes = [];
        this._triggerEvent("removed", removedNodes);
      }
      return this;
    }
    /** @internal */
    _triggerEvent(type, data) {
      const event = data ? new CustomEvent(type, { bubbles: false, detail: data }) : new Event(type);
      this.el.dispatchEvent(event);
      return this;
    }
    /** @internal called to delete the current dynamic style sheet used for our layout */
    _removeStylesheet() {
      if (this._styles) {
        const styleLocation = this.opts.styleInHead ? void 0 : this.el.parentNode;
        Utils.removeStylesheet(this._styleSheetClass, styleLocation);
        delete this._styles;
      }
      return this;
    }
    /** @internal updated/create the CSS styles for row based layout and initial margin setting */
    _updateStyles(forceUpdate = false, maxH) {
      if (forceUpdate) {
        this._removeStylesheet();
      }
      if (maxH === void 0)
        maxH = this.getRow();
      this._updateContainerHeight();
      if (this.opts.cellHeight === 0) {
        return this;
      }
      const cellHeight = this.opts.cellHeight;
      const cellHeightUnit = this.opts.cellHeightUnit;
      const prefix = `.${this._styleSheetClass} > .${this.opts.itemClass}`;
      if (!this._styles) {
        const styleLocation = this.opts.styleInHead ? void 0 : this.el.parentNode;
        this._styles = Utils.createStylesheet(this._styleSheetClass, styleLocation, {
          nonce: this.opts.nonce
        });
        if (!this._styles)
          return this;
        this._styles._max = 0;
        Utils.addCSSRule(this._styles, prefix, `height: ${cellHeight}${cellHeightUnit}`);
        const top = this.opts.marginTop + this.opts.marginUnit;
        const bottom = this.opts.marginBottom + this.opts.marginUnit;
        const right = this.opts.marginRight + this.opts.marginUnit;
        const left = this.opts.marginLeft + this.opts.marginUnit;
        const content = `${prefix} > .grid-stack-item-content`;
        const placeholder = `.${this._styleSheetClass} > .grid-stack-placeholder > .placeholder-content`;
        Utils.addCSSRule(this._styles, content, `top: ${top}; right: ${right}; bottom: ${bottom}; left: ${left};`);
        Utils.addCSSRule(this._styles, placeholder, `top: ${top}; right: ${right}; bottom: ${bottom}; left: ${left};`);
        Utils.addCSSRule(this._styles, `${prefix} > .ui-resizable-n`, `top: ${top};`);
        Utils.addCSSRule(this._styles, `${prefix} > .ui-resizable-s`, `bottom: ${bottom}`);
        Utils.addCSSRule(this._styles, `${prefix} > .ui-resizable-ne`, `right: ${right}; top: ${top}`);
        Utils.addCSSRule(this._styles, `${prefix} > .ui-resizable-e`, `right: ${right}`);
        Utils.addCSSRule(this._styles, `${prefix} > .ui-resizable-se`, `right: ${right}; bottom: ${bottom}`);
        Utils.addCSSRule(this._styles, `${prefix} > .ui-resizable-nw`, `left: ${left}; top: ${top}`);
        Utils.addCSSRule(this._styles, `${prefix} > .ui-resizable-w`, `left: ${left}`);
        Utils.addCSSRule(this._styles, `${prefix} > .ui-resizable-sw`, `left: ${left}; bottom: ${bottom}`);
      }
      maxH = maxH || this._styles._max;
      if (maxH > this._styles._max) {
        const getHeight = (rows) => cellHeight * rows + cellHeightUnit;
        for (let i = this._styles._max + 1; i <= maxH; i++) {
          Utils.addCSSRule(this._styles, `${prefix}[gs-y="${i}"]`, `top: ${getHeight(i)}`);
          Utils.addCSSRule(this._styles, `${prefix}[gs-h="${i + 1}"]`, `height: ${getHeight(i + 1)}`);
        }
        this._styles._max = maxH;
      }
      return this;
    }
    /** @internal */
    _updateContainerHeight() {
      if (!this.engine || this.engine.batchMode)
        return this;
      const parent = this.parentGridNode;
      let row = this.getRow() + this._extraDragRow;
      const cellHeight = this.opts.cellHeight;
      const unit = this.opts.cellHeightUnit;
      if (!cellHeight)
        return this;
      if (!parent) {
        const cssMinHeight = Utils.parseHeight(getComputedStyle(this.el)["minHeight"]);
        if (cssMinHeight.h > 0 && cssMinHeight.unit === unit) {
          const minRow = Math.floor(cssMinHeight.h / cellHeight);
          if (row < minRow) {
            row = minRow;
          }
        }
      }
      this.el.setAttribute("gs-current-row", String(row));
      this.el.style.removeProperty("min-height");
      this.el.style.removeProperty("height");
      if (row) {
        this.el.style[parent ? "minHeight" : "height"] = row * cellHeight + unit;
      }
      if (parent && !parent.grid.engine.batchMode && Utils.shouldSizeToContent(parent)) {
        parent.grid.resizeToContentCBCheck(parent.el);
      }
      return this;
    }
    /** @internal */
    _prepareElement(el, triggerAddEvent = false, node) {
      node = node || this._readAttr(el);
      el.gridstackNode = node;
      node.el = el;
      node.grid = this;
      node = this.engine.addNode(node, triggerAddEvent);
      this._writeAttr(el, node);
      el.classList.add(gridDefaults.itemClass, this.opts.itemClass);
      const sizeToContent = Utils.shouldSizeToContent(node);
      sizeToContent ? el.classList.add("size-to-content") : el.classList.remove("size-to-content");
      if (sizeToContent)
        this.resizeToContentCheck(false, node);
      if (!Utils.lazyLoad(node))
        this.prepareDragDrop(node.el);
      return this;
    }
    /** @internal call to write position x,y,w,h attributes back to element */
    _writePosAttr(el, n) {
      if (n.x !== void 0 && n.x !== null) {
        el.setAttribute("gs-x", String(n.x));
      }
      if (n.y !== void 0 && n.y !== null) {
        el.setAttribute("gs-y", String(n.y));
      }
      n.w > 1 ? el.setAttribute("gs-w", String(n.w)) : el.removeAttribute("gs-w");
      n.h > 1 ? el.setAttribute("gs-h", String(n.h)) : el.removeAttribute("gs-h");
      return this;
    }
    /** @internal call to write any default attributes back to element */
    _writeAttr(el, node) {
      if (!node)
        return this;
      this._writePosAttr(el, node);
      const attrs = {
        // autoPosition: 'gs-auto-position', // no need to write out as already in node and doesn't affect CSS
        noResize: "gs-no-resize",
        noMove: "gs-no-move",
        locked: "gs-locked",
        id: "gs-id",
        sizeToContent: "gs-size-to-content"
      };
      for (const key in attrs) {
        if (node[key]) {
          el.setAttribute(attrs[key], String(node[key]));
        } else {
          el.removeAttribute(attrs[key]);
        }
      }
      return this;
    }
    /** @internal call to read any default attributes from element */
    _readAttr(el, clearDefaultAttr = true) {
      const n = {};
      n.x = Utils.toNumber(el.getAttribute("gs-x"));
      n.y = Utils.toNumber(el.getAttribute("gs-y"));
      n.w = Utils.toNumber(el.getAttribute("gs-w"));
      n.h = Utils.toNumber(el.getAttribute("gs-h"));
      n.autoPosition = Utils.toBool(el.getAttribute("gs-auto-position"));
      n.noResize = Utils.toBool(el.getAttribute("gs-no-resize"));
      n.noMove = Utils.toBool(el.getAttribute("gs-no-move"));
      n.locked = Utils.toBool(el.getAttribute("gs-locked"));
      const attr = el.getAttribute("gs-size-to-content");
      if (attr) {
        if (attr === "true" || attr === "false")
          n.sizeToContent = Utils.toBool(attr);
        else
          n.sizeToContent = parseInt(attr, 10);
      }
      n.id = el.getAttribute("gs-id");
      n.maxW = Utils.toNumber(el.getAttribute("gs-max-w"));
      n.minW = Utils.toNumber(el.getAttribute("gs-min-w"));
      n.maxH = Utils.toNumber(el.getAttribute("gs-max-h"));
      n.minH = Utils.toNumber(el.getAttribute("gs-min-h"));
      if (clearDefaultAttr) {
        if (n.w === 1)
          el.removeAttribute("gs-w");
        if (n.h === 1)
          el.removeAttribute("gs-h");
        if (n.maxW)
          el.removeAttribute("gs-max-w");
        if (n.minW)
          el.removeAttribute("gs-min-w");
        if (n.maxH)
          el.removeAttribute("gs-max-h");
        if (n.minH)
          el.removeAttribute("gs-min-h");
      }
      for (const key in n) {
        if (!n.hasOwnProperty(key))
          return;
        if (!n[key] && n[key] !== 0 && key !== "gs-size-to-content") {
          delete n[key];
        }
      }
      return n;
    }
    /** @internal */
    _setStaticClass() {
      const classes = ["grid-stack-static"];
      if (this.opts.staticGrid) {
        this.el.classList.add(...classes);
        this.el.setAttribute("gs-static", "true");
      } else {
        this.el.classList.remove(...classes);
        this.el.removeAttribute("gs-static");
      }
      return this;
    }
    /**
     * called when we are being resized - check if the one Column Mode needs to be turned on/off
     * and remember the prev columns we used, or get our count from parent, as well as check for cellHeight==='auto' (square)
     * or `sizeToContent` gridItem options.
     */
    onResize(clientWidth = this.el?.clientWidth) {
      if (!clientWidth)
        return;
      if (this.prevWidth === clientWidth)
        return;
      this.prevWidth = clientWidth;
      this.batchUpdate();
      let columnChanged = false;
      if (this._autoColumn && this.parentGridNode) {
        if (this.opts.column !== this.parentGridNode.w) {
          this.column(this.parentGridNode.w, this.opts.layout || "list");
          columnChanged = true;
        }
      } else {
        columnChanged = this.checkDynamicColumn();
      }
      if (this._isAutoCellHeight)
        this.cellHeight();
      this.engine.nodes.forEach((n) => {
        if (n.subGrid)
          n.subGrid.onResize();
      });
      if (!this._skipInitialResize)
        this.resizeToContentCheck(columnChanged);
      delete this._skipInitialResize;
      this.batchUpdate(false);
      return this;
    }
    /** resizes content for given node (or all) if shouldSizeToContent() is true */
    resizeToContentCheck(delay = false, n = void 0) {
      if (!this.engine)
        return;
      if (delay && this.hasAnimationCSS())
        return setTimeout(() => this.resizeToContentCheck(false, n), this.animationDelay);
      if (n) {
        if (Utils.shouldSizeToContent(n))
          this.resizeToContentCBCheck(n.el);
      } else if (this.engine.nodes.some((n2) => Utils.shouldSizeToContent(n2))) {
        const nodes = [...this.engine.nodes];
        this.batchUpdate();
        nodes.forEach((n2) => {
          if (Utils.shouldSizeToContent(n2))
            this.resizeToContentCBCheck(n2.el);
        });
        this.batchUpdate(false);
      }
      if (this._gsEventHandler["resizecontent"])
        this._gsEventHandler["resizecontent"](null, n ? [n] : this.engine.nodes);
    }
    /** add or remove the grid element size event handler */
    _updateResizeEvent(forceRemove = false) {
      const trackSize = !this.parentGridNode && (this._isAutoCellHeight || this.opts.sizeToContent || this.opts.columnOpts || this.engine.nodes.find((n) => n.sizeToContent));
      if (!forceRemove && trackSize && !this.resizeObserver) {
        this._sizeThrottle = Utils.throttle(() => this.onResize(), this.opts.cellHeightThrottle);
        this.resizeObserver = new ResizeObserver(() => this._sizeThrottle());
        this.resizeObserver.observe(this.el);
        this._skipInitialResize = true;
      } else if ((forceRemove || !trackSize) && this.resizeObserver) {
        this.resizeObserver.disconnect();
        delete this.resizeObserver;
        delete this._sizeThrottle;
      }
      return this;
    }
    /** @internal convert a potential selector into actual element */
    static getElement(els = ".grid-stack-item") {
      return Utils.getElement(els);
    }
    /** @internal */
    static getElements(els = ".grid-stack-item") {
      return Utils.getElements(els);
    }
    /** @internal */
    static getGridElement(els) {
      return _GridStack.getElement(els);
    }
    /** @internal */
    static getGridElements(els) {
      return Utils.getElements(els);
    }
    /** @internal initialize margin top/bottom/left/right and units */
    _initMargin() {
      let data;
      let margin = 0;
      let margins = [];
      if (typeof this.opts.margin === "string") {
        margins = this.opts.margin.split(" ");
      }
      if (margins.length === 2) {
        this.opts.marginTop = this.opts.marginBottom = margins[0];
        this.opts.marginLeft = this.opts.marginRight = margins[1];
      } else if (margins.length === 4) {
        this.opts.marginTop = margins[0];
        this.opts.marginRight = margins[1];
        this.opts.marginBottom = margins[2];
        this.opts.marginLeft = margins[3];
      } else {
        data = Utils.parseHeight(this.opts.margin);
        this.opts.marginUnit = data.unit;
        margin = this.opts.margin = data.h;
      }
      if (this.opts.marginTop === void 0) {
        this.opts.marginTop = margin;
      } else {
        data = Utils.parseHeight(this.opts.marginTop);
        this.opts.marginTop = data.h;
        delete this.opts.margin;
      }
      if (this.opts.marginBottom === void 0) {
        this.opts.marginBottom = margin;
      } else {
        data = Utils.parseHeight(this.opts.marginBottom);
        this.opts.marginBottom = data.h;
        delete this.opts.margin;
      }
      if (this.opts.marginRight === void 0) {
        this.opts.marginRight = margin;
      } else {
        data = Utils.parseHeight(this.opts.marginRight);
        this.opts.marginRight = data.h;
        delete this.opts.margin;
      }
      if (this.opts.marginLeft === void 0) {
        this.opts.marginLeft = margin;
      } else {
        data = Utils.parseHeight(this.opts.marginLeft);
        this.opts.marginLeft = data.h;
        delete this.opts.margin;
      }
      this.opts.marginUnit = data.unit;
      if (this.opts.marginTop === this.opts.marginBottom && this.opts.marginLeft === this.opts.marginRight && this.opts.marginTop === this.opts.marginRight) {
        this.opts.margin = this.opts.marginTop;
      }
      return this;
    }
    /* ===========================================================================================
     * drag&drop methods that used to be stubbed out and implemented in dd-gridstack.ts
     * but caused loading issues in prod - see https://github.com/gridstack/gridstack.js/issues/2039
     * ===========================================================================================
     */
    /** get the global (but static to this code) DD implementation */
    static getDD() {
      return dd;
    }
    /**
     * call to setup dragging in from the outside (say toolbar), by specifying the class selection and options.
     * Called during GridStack.init() as options, but can also be called directly (last param are used) in case the toolbar
     * is dynamically create and needs to be set later.
     * @param dragIn string selector (ex: '.sidebar-item') or list of dom elements
     * @param dragInOptions options - see DDDragOpt. (default: {handle: '.grid-stack-item-content', appendTo: 'body'}
     * @param widgets GridStackWidget def to assign to each element which defines what to create on drop
     * @param root optional root which defaults to document (for shadow dom pass the parent HTMLDocument)
     */
    static setupDragIn(dragIn, dragInOptions, widgets, root = document) {
      if (dragInOptions?.pause !== void 0) {
        DDManager.pauseDrag = dragInOptions.pause;
      }
      dragInOptions = { appendTo: "body", helper: "clone", ...dragInOptions || {} };
      const els = typeof dragIn === "string" ? Utils.getElements(dragIn, root) : dragIn;
      els.forEach((el, i) => {
        if (!dd.isDraggable(el))
          dd.dragIn(el, dragInOptions);
        if (widgets?.[i])
          el.gridstackNode = widgets[i];
      });
    }
    /**
     * Enables/Disables dragging by the user of specific grid element. If you want all items, and have it affect future items, use enableMove() instead. No-op for static grids.
     * IF you are looking to prevent an item from moving (due to being pushed around by another during collision) use locked property instead.
     * @param els widget or selector to modify.
     * @param val if true widget will be draggable, assuming the parent grid isn't noMove or static.
     */
    movable(els, val) {
      if (this.opts.staticGrid)
        return this;
      _GridStack.getElements(els).forEach((el) => {
        const n = el.gridstackNode;
        if (!n)
          return;
        val ? delete n.noMove : n.noMove = true;
        this.prepareDragDrop(n.el);
      });
      return this;
    }
    /**
     * Enables/Disables user resizing of specific grid element. If you want all items, and have it affect future items, use enableResize() instead. No-op for static grids.
     * @param els  widget or selector to modify
     * @param val  if true widget will be resizable, assuming the parent grid isn't noResize or static.
     */
    resizable(els, val) {
      if (this.opts.staticGrid)
        return this;
      _GridStack.getElements(els).forEach((el) => {
        const n = el.gridstackNode;
        if (!n)
          return;
        val ? delete n.noResize : n.noResize = true;
        this.prepareDragDrop(n.el);
      });
      return this;
    }
    /**
     * Temporarily disables widgets moving/resizing.
     * If you want a more permanent way (which freezes up resources) use `setStatic(true)` instead.
     * Note: no-op for static grid
     * This is a shortcut for:
     * @example
     *  grid.enableMove(false);
     *  grid.enableResize(false);
     * @param recurse true (default) if sub-grids also get updated
     */
    disable(recurse = true) {
      if (this.opts.staticGrid)
        return;
      this.enableMove(false, recurse);
      this.enableResize(false, recurse);
      this._triggerEvent("disable");
      return this;
    }
    /**
     * Re-enables widgets moving/resizing - see disable().
     * Note: no-op for static grid.
     * This is a shortcut for:
     * @example
     *  grid.enableMove(true);
     *  grid.enableResize(true);
     * @param recurse true (default) if sub-grids also get updated
     */
    enable(recurse = true) {
      if (this.opts.staticGrid)
        return;
      this.enableMove(true, recurse);
      this.enableResize(true, recurse);
      this._triggerEvent("enable");
      return this;
    }
    /**
     * Enables/disables widget moving. No-op for static grids, and locally defined items still overrule
     * @param recurse true (default) if sub-grids also get updated
     */
    enableMove(doEnable, recurse = true) {
      if (this.opts.staticGrid)
        return this;
      doEnable ? delete this.opts.disableDrag : this.opts.disableDrag = true;
      this.engine.nodes.forEach((n) => {
        this.prepareDragDrop(n.el);
        if (n.subGrid && recurse)
          n.subGrid.enableMove(doEnable, recurse);
      });
      return this;
    }
    /**
     * Enables/disables widget resizing. No-op for static grids.
     * @param recurse true (default) if sub-grids also get updated
     */
    enableResize(doEnable, recurse = true) {
      if (this.opts.staticGrid)
        return this;
      doEnable ? delete this.opts.disableResize : this.opts.disableResize = true;
      this.engine.nodes.forEach((n) => {
        this.prepareDragDrop(n.el);
        if (n.subGrid && recurse)
          n.subGrid.enableResize(doEnable, recurse);
      });
      return this;
    }
    /** @internal call when drag (and drop) needs to be cancelled (Esc key) */
    cancelDrag() {
      const n = this._placeholder?.gridstackNode;
      if (!n)
        return;
      if (n._isExternal) {
        n._isAboutToRemove = true;
        this.engine.removeNode(n);
      } else if (n._isAboutToRemove) {
        _GridStack._itemRemoving(n.el, false);
      }
      this.engine.restoreInitial();
    }
    /** @internal removes any drag&drop present (called during destroy) */
    _removeDD(el) {
      dd.draggable(el, "destroy").resizable(el, "destroy");
      if (el.gridstackNode) {
        delete el.gridstackNode._initDD;
      }
      delete el.ddElement;
      return this;
    }
    /** @internal called to add drag over to support widgets being added externally */
    _setupAcceptWidget() {
      if (this.opts.staticGrid || !this.opts.acceptWidgets && !this.opts.removable) {
        dd.droppable(this.el, "destroy");
        return this;
      }
      let cellHeight, cellWidth;
      const onDrag = (event, el, helper) => {
        helper = helper || el;
        const node = helper.gridstackNode;
        if (!node)
          return;
        if (!node.grid?.el) {
          helper.style.transform = `scale(${1 / this.dragTransform.xScale},${1 / this.dragTransform.yScale})`;
          const helperRect = helper.getBoundingClientRect();
          helper.style.left = helperRect.x + (this.dragTransform.xScale - 1) * (event.clientX - helperRect.x) / this.dragTransform.xScale + "px";
          helper.style.top = helperRect.y + (this.dragTransform.yScale - 1) * (event.clientY - helperRect.y) / this.dragTransform.yScale + "px";
          helper.style.transformOrigin = `0px 0px`;
        }
        let { top, left } = helper.getBoundingClientRect();
        const rect = this.el.getBoundingClientRect();
        left -= rect.left;
        top -= rect.top;
        const ui = {
          position: {
            top: top * this.dragTransform.xScale,
            left: left * this.dragTransform.yScale
          }
        };
        if (node._temporaryRemoved) {
          node.x = Math.max(0, Math.round(left / cellWidth));
          node.y = Math.max(0, Math.round(top / cellHeight));
          delete node.autoPosition;
          this.engine.nodeBoundFix(node);
          if (!this.engine.willItFit(node)) {
            node.autoPosition = true;
            if (!this.engine.willItFit(node)) {
              dd.off(el, "drag");
              return;
            }
            if (node._willFitPos) {
              Utils.copyPos(node, node._willFitPos);
              delete node._willFitPos;
            }
          }
          this._onStartMoving(helper, event, ui, node, cellWidth, cellHeight);
        } else {
          this._dragOrResize(helper, event, ui, node, cellWidth, cellHeight);
        }
      };
      dd.droppable(this.el, {
        accept: (el) => {
          const node = el.gridstackNode || this._readAttr(el, false);
          if (node?.grid === this)
            return true;
          if (!this.opts.acceptWidgets)
            return false;
          let canAccept = true;
          if (typeof this.opts.acceptWidgets === "function") {
            canAccept = this.opts.acceptWidgets(el);
          } else {
            const selector = this.opts.acceptWidgets === true ? ".grid-stack-item" : this.opts.acceptWidgets;
            canAccept = el.matches(selector);
          }
          if (canAccept && node && this.opts.maxRow) {
            const n = { w: node.w, h: node.h, minW: node.minW, minH: node.minH };
            canAccept = this.engine.willItFit(n);
          }
          return canAccept;
        }
      }).on(this.el, "dropover", (event, el, helper) => {
        let node = helper?.gridstackNode || el.gridstackNode;
        if (node?.grid === this && !node._temporaryRemoved) {
          return false;
        }
        if (node?._sidebarOrig) {
          node.w = node._sidebarOrig.w;
          node.h = node._sidebarOrig.h;
        }
        if (node?.grid && node.grid !== this && !node._temporaryRemoved) {
          const otherGrid = node.grid;
          otherGrid._leave(el, helper);
        }
        helper = helper || el;
        cellWidth = this.cellWidth();
        cellHeight = this.getCellHeight(true);
        if (!node) {
          const attr = helper.getAttribute("data-gs-widget") || helper.getAttribute("gridstacknode");
          if (attr) {
            try {
              node = JSON.parse(attr);
            } catch (error) {
              console.error("Gridstack dropover: Bad JSON format: ", attr);
            }
            helper.removeAttribute("data-gs-widget");
            helper.removeAttribute("gridstacknode");
          }
          if (!node)
            node = this._readAttr(helper);
          node._sidebarOrig = { w: node.w, h: node.h };
        }
        if (!node.grid) {
          if (!node.el)
            node = { ...node };
          node._isExternal = true;
          helper.gridstackNode = node;
        }
        const w = node.w || Math.round(helper.offsetWidth / cellWidth) || 1;
        const h = node.h || Math.round(helper.offsetHeight / cellHeight) || 1;
        if (node.grid && node.grid !== this) {
          if (!el._gridstackNodeOrig)
            el._gridstackNodeOrig = node;
          el.gridstackNode = node = { ...node, w, h, grid: this };
          delete node.x;
          delete node.y;
          this.engine.cleanupNode(node).nodeBoundFix(node);
          node._initDD = node._isExternal = // DOM needs to be re-parented on a drop
          node._temporaryRemoved = true;
        } else {
          node.w = w;
          node.h = h;
          node._temporaryRemoved = true;
        }
        _GridStack._itemRemoving(node.el, false);
        dd.on(el, "drag", onDrag);
        onDrag(event, el, helper);
        return false;
      }).on(this.el, "dropout", (event, el, helper) => {
        const node = helper?.gridstackNode || el.gridstackNode;
        if (!node)
          return false;
        if (!node.grid || node.grid === this) {
          this._leave(el, helper);
          if (this._isTemp) {
            this.removeAsSubGrid(node);
          }
        }
        return false;
      }).on(this.el, "drop", (event, el, helper) => {
        const node = helper?.gridstackNode || el.gridstackNode;
        if (node?.grid === this && !node._isExternal)
          return false;
        const wasAdded = !!this.placeholder.parentElement;
        const wasSidebar = el !== helper;
        this.placeholder.remove();
        delete this.placeholder.gridstackNode;
        const noAnim = wasAdded && this.opts.animate;
        if (noAnim)
          this.setAnimation(false);
        const origNode = el._gridstackNodeOrig;
        delete el._gridstackNodeOrig;
        if (wasAdded && origNode?.grid && origNode.grid !== this) {
          const oGrid = origNode.grid;
          oGrid.engine.removeNodeFromLayoutCache(origNode);
          oGrid.engine.removedNodes.push(origNode);
          oGrid._triggerRemoveEvent()._triggerChangeEvent();
          if (oGrid.parentGridNode && !oGrid.engine.nodes.length && oGrid.opts.subGridDynamic) {
            oGrid.removeAsSubGrid();
          }
        }
        if (!node)
          return false;
        if (wasAdded) {
          this.engine.cleanupNode(node);
          node.grid = this;
        }
        delete node.grid?._isTemp;
        dd.off(el, "drag");
        if (helper !== el) {
          helper.remove();
          el = helper;
        } else {
          el.remove();
        }
        this._removeDD(el);
        if (!wasAdded)
          return false;
        const subGrid = node.subGrid?.el?.gridstack;
        Utils.copyPos(node, this._readAttr(this.placeholder));
        Utils.removePositioningStyles(el);
        if (wasSidebar && (node.content || node.subGridOpts || _GridStack.addRemoveCB)) {
          delete node.el;
          el = this.addWidget(node);
        } else {
          this._prepareElement(el, true, node);
          this.el.appendChild(el);
          this.resizeToContentCheck(false, node);
          if (subGrid) {
            subGrid.parentGridNode = node;
            if (!subGrid.opts.styleInHead)
              subGrid._updateStyles(true);
          }
          this._updateContainerHeight();
        }
        this.engine.addedNodes.push(node);
        this._triggerAddEvent();
        this._triggerChangeEvent();
        this.engine.endUpdate();
        if (this._gsEventHandler["dropped"]) {
          this._gsEventHandler["dropped"]({ ...event, type: "dropped" }, origNode && origNode.grid ? origNode : void 0, node);
        }
        if (noAnim)
          this.setAnimation(this.opts.animate, true);
        return false;
      });
      return this;
    }
    /** @internal mark item for removal */
    static _itemRemoving(el, remove) {
      if (!el)
        return;
      const node = el ? el.gridstackNode : void 0;
      if (!node?.grid || el.classList.contains(node.grid.opts.removableOptions.decline))
        return;
      remove ? node._isAboutToRemove = true : delete node._isAboutToRemove;
      remove ? el.classList.add("grid-stack-item-removing") : el.classList.remove("grid-stack-item-removing");
    }
    /** @internal called to setup a trash drop zone if the user specifies it */
    _setupRemoveDrop() {
      if (typeof this.opts.removable !== "string")
        return this;
      const trashEl = document.querySelector(this.opts.removable);
      if (!trashEl)
        return this;
      if (!this.opts.staticGrid && !dd.isDroppable(trashEl)) {
        dd.droppable(trashEl, this.opts.removableOptions).on(trashEl, "dropover", (event, el) => _GridStack._itemRemoving(el, true)).on(trashEl, "dropout", (event, el) => _GridStack._itemRemoving(el, false));
      }
      return this;
    }
    /**
     * prepares the element for drag&drop - this is normally called by makeWidget() unless are are delay loading
     * @param el GridItemHTMLElement of the widget
     * @param [force=false]
     * */
    prepareDragDrop(el, force = false) {
      const node = el?.gridstackNode;
      if (!node)
        return;
      const noMove = node.noMove || this.opts.disableDrag;
      const noResize = node.noResize || this.opts.disableResize;
      const disable = this.opts.staticGrid || noMove && noResize;
      if (force || disable) {
        if (node._initDD) {
          this._removeDD(el);
          delete node._initDD;
        }
        if (disable)
          el.classList.add("ui-draggable-disabled", "ui-resizable-disabled");
        if (!force)
          return this;
      }
      if (!node._initDD) {
        let cellWidth;
        let cellHeight;
        const onStartMoving = (event, ui) => {
          if (this._gsEventHandler[event.type]) {
            this._gsEventHandler[event.type](event, event.target);
          }
          cellWidth = this.cellWidth();
          cellHeight = this.getCellHeight(true);
          this._onStartMoving(el, event, ui, node, cellWidth, cellHeight);
        };
        const dragOrResize = (event, ui) => {
          this._dragOrResize(el, event, ui, node, cellWidth, cellHeight);
        };
        const onEndMoving = (event) => {
          this.placeholder.remove();
          delete this.placeholder.gridstackNode;
          delete node._moving;
          delete node._event;
          delete node._lastTried;
          const widthChanged = node.w !== node._orig.w;
          const target = event.target;
          if (!target.gridstackNode || target.gridstackNode.grid !== this)
            return;
          node.el = target;
          if (node._isAboutToRemove) {
            const grid2 = el.gridstackNode.grid;
            if (grid2._gsEventHandler[event.type]) {
              grid2._gsEventHandler[event.type](event, target);
            }
            grid2.engine.nodes.push(node);
            grid2.removeWidget(el, true, true);
          } else {
            Utils.removePositioningStyles(target);
            if (node._temporaryRemoved) {
              Utils.copyPos(node, node._orig);
              this._writePosAttr(target, node);
              this.engine.addNode(node);
            } else {
              this._writePosAttr(target, node);
            }
            if (this._gsEventHandler[event.type]) {
              this._gsEventHandler[event.type](event, target);
            }
          }
          this._extraDragRow = 0;
          this._updateContainerHeight();
          this._triggerChangeEvent();
          this.engine.endUpdate();
          if (event.type === "resizestop") {
            if (Number.isInteger(node.sizeToContent))
              node.sizeToContent = node.h;
            this.resizeToContentCheck(widthChanged, node);
          }
        };
        dd.draggable(el, {
          start: onStartMoving,
          stop: onEndMoving,
          drag: dragOrResize
        }).resizable(el, {
          start: onStartMoving,
          stop: onEndMoving,
          resize: dragOrResize
        });
        node._initDD = true;
      }
      dd.draggable(el, noMove ? "disable" : "enable").resizable(el, noResize ? "disable" : "enable");
      return this;
    }
    /** @internal handles actual drag/resize start */
    _onStartMoving(el, event, ui, node, cellWidth, cellHeight) {
      this.engine.cleanNodes().beginUpdate(node);
      this._writePosAttr(this.placeholder, node);
      this.el.appendChild(this.placeholder);
      this.placeholder.gridstackNode = node;
      if (node.grid?.el) {
        this.dragTransform = Utils.getValuesFromTransformedElement(el);
      } else if (this.placeholder && this.placeholder.closest(".grid-stack")) {
        const gridEl = this.placeholder.closest(".grid-stack");
        this.dragTransform = Utils.getValuesFromTransformedElement(gridEl);
      } else {
        this.dragTransform = {
          xScale: 1,
          xOffset: 0,
          yScale: 1,
          yOffset: 0
        };
      }
      node.el = this.placeholder;
      node._lastUiPosition = ui.position;
      node._prevYPix = ui.position.top;
      node._moving = event.type === "dragstart";
      delete node._lastTried;
      if (event.type === "dropover" && node._temporaryRemoved) {
        this.engine.addNode(node);
        node._moving = true;
      }
      this.engine.cacheRects(cellWidth, cellHeight, this.opts.marginTop, this.opts.marginRight, this.opts.marginBottom, this.opts.marginLeft);
      if (event.type === "resizestart") {
        const colLeft = this.getColumn() - node.x;
        const rowLeft = (this.opts.maxRow || Number.MAX_SAFE_INTEGER) - node.y;
        dd.resizable(el, "option", "minWidth", cellWidth * Math.min(node.minW || 1, colLeft)).resizable(el, "option", "minHeight", cellHeight * Math.min(node.minH || 1, rowLeft)).resizable(el, "option", "maxWidth", cellWidth * Math.min(node.maxW || Number.MAX_SAFE_INTEGER, colLeft)).resizable(el, "option", "maxWidthMoveLeft", cellWidth * Math.min(node.maxW || Number.MAX_SAFE_INTEGER, node.x + node.w)).resizable(el, "option", "maxHeight", cellHeight * Math.min(node.maxH || Number.MAX_SAFE_INTEGER, rowLeft)).resizable(el, "option", "maxHeightMoveUp", cellHeight * Math.min(node.maxH || Number.MAX_SAFE_INTEGER, node.y + node.h));
      }
    }
    /** @internal handles actual drag/resize */
    _dragOrResize(el, event, ui, node, cellWidth, cellHeight) {
      const p = { ...node._orig };
      let resizing;
      let mLeft = this.opts.marginLeft, mRight = this.opts.marginRight, mTop = this.opts.marginTop, mBottom = this.opts.marginBottom;
      const mHeight = Math.round(cellHeight * 0.1), mWidth = Math.round(cellWidth * 0.1);
      mLeft = Math.min(mLeft, mWidth);
      mRight = Math.min(mRight, mWidth);
      mTop = Math.min(mTop, mHeight);
      mBottom = Math.min(mBottom, mHeight);
      if (event.type === "drag") {
        if (node._temporaryRemoved)
          return;
        const distance = ui.position.top - node._prevYPix;
        node._prevYPix = ui.position.top;
        if (this.opts.draggable.scroll !== false) {
          Utils.updateScrollPosition(el, ui.position, distance);
        }
        const left = ui.position.left + (ui.position.left > node._lastUiPosition.left ? -mRight : mLeft);
        const top = ui.position.top + (ui.position.top > node._lastUiPosition.top ? -mBottom : mTop);
        p.x = Math.round(left / cellWidth);
        p.y = Math.round(top / cellHeight);
        const prev = this._extraDragRow;
        if (this.engine.collide(node, p)) {
          const row = this.getRow();
          let extra = Math.max(0, p.y + node.h - row);
          if (this.opts.maxRow && row + extra > this.opts.maxRow) {
            extra = Math.max(0, this.opts.maxRow - row);
          }
          this._extraDragRow = extra;
        } else
          this._extraDragRow = 0;
        if (this._extraDragRow !== prev)
          this._updateContainerHeight();
        if (node.x === p.x && node.y === p.y)
          return;
      } else if (event.type === "resize") {
        if (p.x < 0)
          return;
        Utils.updateScrollResize(event, el, cellHeight);
        p.w = Math.round((ui.size.width - mLeft) / cellWidth);
        p.h = Math.round((ui.size.height - mTop) / cellHeight);
        if (node.w === p.w && node.h === p.h)
          return;
        if (node._lastTried && node._lastTried.w === p.w && node._lastTried.h === p.h)
          return;
        const left = ui.position.left + mLeft;
        const top = ui.position.top + mTop;
        p.x = Math.round(left / cellWidth);
        p.y = Math.round(top / cellHeight);
        resizing = true;
      }
      node._event = event;
      node._lastTried = p;
      const rect = {
        x: ui.position.left + mLeft,
        y: ui.position.top + mTop,
        w: (ui.size ? ui.size.width : node.w * cellWidth) - mLeft - mRight,
        h: (ui.size ? ui.size.height : node.h * cellHeight) - mTop - mBottom
      };
      if (this.engine.moveNodeCheck(node, { ...p, cellWidth, cellHeight, rect, resizing })) {
        node._lastUiPosition = ui.position;
        this.engine.cacheRects(cellWidth, cellHeight, mTop, mRight, mBottom, mLeft);
        delete node._skipDown;
        if (resizing && node.subGrid)
          node.subGrid.onResize();
        this._extraDragRow = 0;
        this._updateContainerHeight();
        const target = event.target;
        if (!node._sidebarOrig) {
          this._writePosAttr(target, node);
        }
        if (this._gsEventHandler[event.type]) {
          this._gsEventHandler[event.type](event, target);
        }
      }
    }
    /** @internal called when item leaving our area by either cursor dropout event
     * or shape is outside our boundaries. remove it from us, and mark temporary if this was
     * our item to start with else restore prev node values from prev grid it came from.
     */
    _leave(el, helper) {
      helper = helper || el;
      const node = helper.gridstackNode;
      if (!node)
        return;
      helper.style.transform = helper.style.transformOrigin = null;
      dd.off(el, "drag");
      if (node._temporaryRemoved)
        return;
      node._temporaryRemoved = true;
      this.engine.removeNode(node);
      node.el = node._isExternal && helper ? helper : el;
      const sidebarOrig = node._sidebarOrig;
      if (node._isExternal)
        this.engine.cleanupNode(node);
      node._sidebarOrig = sidebarOrig;
      if (this.opts.removable === true) {
        _GridStack._itemRemoving(el, true);
      }
      if (el._gridstackNodeOrig) {
        el.gridstackNode = el._gridstackNodeOrig;
        delete el._gridstackNodeOrig;
      } else if (node._isExternal) {
        this.engine.restoreInitial();
      }
    }
    // legacy method removed
    commit() {
      obsolete(this, this.batchUpdate(false), "commit", "batchUpdate", "5.2");
      return this;
    }
  };
  GridStack.renderCB = (el, w) => {
    if (el && w?.content)
      el.textContent = w.content;
  };
  GridStack.resizeToContentParent = ".grid-stack-item-content";
  GridStack.Utils = Utils;
  GridStack.Engine = GridStackEngine;
  GridStack.GDRev = "11.5.1";

  // src/dashboard-core.ts
  GridStack.renderCB = (el, w) => {
    el.innerHTML = w.content ?? "";
  };
  var PREFIX = "querychat-dashboard-";
  var grid = null;
  var suppressChange = false;
  var initialized = false;
  function qs(sel) {
    return document.querySelector(sel);
  }
  function inputIds() {
    const drawer = qs(".querychat-dash-drawer");
    if (!drawer) return {};
    try {
      return JSON.parse(drawer.getAttribute("data-qcdash-inputs") || "{}");
    } catch {
      return {};
    }
  }
  function setInput(shiny, name, value) {
    const id = inputIds()[name];
    if (id && shiny.setInputValue) {
      shiny.setInputValue(id, value, { priority: "event" });
    }
  }
  function ensureGrid(shiny) {
    if (grid) return grid;
    const el = qs(".querychat-dash-canvas");
    if (!el) throw new Error("querychat dashboard canvas missing");
    grid = GridStack.init(
      { column: 12, cellHeight: 90, margin: 6, float: false, animate: true },
      el
    );
    grid.on("change", (_ev, nodes) => {
      if (suppressChange || !nodes?.length) return;
      const placements = nodes.filter(
        (n) => !!n.el?.getAttribute("data-card-name")
      ).map((n) => ({
        name: n.el.getAttribute("data-card-name"),
        x: n.x ?? 0,
        y: n.y ?? 0,
        w: n.w ?? 1,
        h: n.h ?? 1
      }));
      if (placements.length) setInput(shiny, "dashboard_layout_change", placements);
    });
    return grid;
  }
  async function bindInto(shiny, el) {
    shiny.initializeInputs?.(el);
    await shiny.bindAll?.(el);
  }
  function cardItem(name) {
    return document.querySelector(
      `.grid-stack-item[data-card-name="${name}"]`
    );
  }
  function upsertCard(shiny, msg) {
    const g = ensureGrid(shiny);
    suppressChange = true;
    try {
      const existing = cardItem(msg.name);
      if (existing) {
        shiny.unbindAll?.(existing);
        g.removeWidget(existing, true);
      }
      const content = `<button class="querychat-dash-card-remove" title="Remove">\u2715</button>${msg.html}`;
      const el = g.addWidget({
        x: msg.layout.x,
        y: msg.layout.y,
        w: msg.layout.w,
        h: msg.layout.h,
        content
      });
      el.setAttribute("data-card-name", msg.name);
      el.querySelector(".querychat-dash-card-remove")?.addEventListener(
        "click",
        () => setInput(shiny, "dashboard_remove_card", msg.name)
      );
      void bindInto(shiny, el);
    } finally {
      suppressChange = false;
    }
  }
  function removeCard(shiny, msg) {
    const el = cardItem(msg.name);
    if (!el || !grid) return;
    suppressChange = true;
    try {
      shiny.unbindAll?.(el);
      grid.removeWidget(el);
    } finally {
      suppressChange = false;
    }
  }
  function canvasReset(shiny, msg) {
    const g = ensureGrid(shiny);
    g.getGridItems().forEach((el) => shiny.unbindAll?.(el));
    suppressChange = true;
    try {
      g.removeAll();
    } finally {
      suppressChange = false;
    }
    const title = qs(".querychat-dash-title");
    if (title) title.textContent = msg.title;
  }
  function applyLayout(msg) {
    if (!grid) return;
    suppressChange = true;
    try {
      for (const p of msg.placements) {
        const el = cardItem(p.name);
        if (el) grid.update(el, { x: p.x, y: p.y, w: p.w, h: p.h });
      }
    } finally {
      suppressChange = false;
    }
  }
  var chatHome = null;
  function reparentChat(intoDrawer) {
    const chat = qs(".querychat");
    const slot = qs(".querychat-dash-chat-slot");
    if (!chat || !slot) return;
    if (intoDrawer) {
      if (chatHome) return;
      const parent = chat.parentElement;
      if (!parent) return;
      chatHome = { parent, next: chat.nextSibling };
      slot.appendChild(chat);
    } else if (chatHome) {
      chatHome.parent.insertBefore(chat, chatHome.next);
      chatHome = null;
    }
    window.dispatchEvent(new Event("resize"));
  }
  function toggleDrawer(shiny, msg) {
    const drawer = qs(".querychat-dash-drawer");
    if (!drawer) return;
    if (msg.open) {
      drawer.removeAttribute("hidden");
      ensureGrid(shiny);
      reparentChat(true);
    } else {
      drawer.setAttribute("hidden", "");
      reparentChat(false);
    }
  }
  function updatePalette(shiny, msg) {
    const wrap = qs(".querychat-dash-palette-items");
    if (!wrap) return;
    wrap.innerHTML = msg.html;
    wrap.querySelectorAll(".querychat-dash-palette-item").forEach((item) => {
      item.addEventListener(
        "dblclick",
        () => setInput(shiny, "dashboard_palette_add", {
          id: item.getAttribute("data-palette-id")
        })
      );
      item.addEventListener("dragend", (ev) => {
        const canvas = qs(".querychat-dash-canvas");
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const inside = ev.clientX >= rect.left && ev.clientX <= rect.right && ev.clientY >= rect.top && ev.clientY <= rect.bottom;
        if (inside) {
          setInput(shiny, "dashboard_palette_add", {
            id: item.getAttribute("data-palette-id")
          });
        }
      });
    });
  }
  function updateBadge(msg) {
    const badge = qs(".querychat-dash-badge");
    const count = qs(".querychat-dash-badge-count");
    if (!badge || !count) return;
    count.textContent = String(msg.count);
    if (msg.count > 0) {
      badge.removeAttribute("hidden");
    } else {
      badge.setAttribute("hidden", "");
    }
  }
  function updateHistory(msg) {
    qs(".querychat-dash-undo")?.toggleAttribute(
      "disabled",
      !msg.can_undo
    );
    qs(".querychat-dash-redo")?.toggleAttribute(
      "disabled",
      !msg.can_redo
    );
  }
  function updateAutogen(msg) {
    qs(".querychat-dash-autogen-spinner")?.toggleAttribute("hidden", !msg.active);
  }
  function wireStaticControls(shiny) {
    qs(".querychat-dash-close")?.addEventListener(
      "click",
      () => setInput(shiny, "dashboard_close", Date.now())
    );
    qs(".querychat-dash-undo")?.addEventListener(
      "click",
      () => setInput(shiny, "dashboard_undo", Date.now())
    );
    qs(".querychat-dash-redo")?.addEventListener(
      "click",
      () => setInput(shiny, "dashboard_redo", Date.now())
    );
    qs(".querychat-dash-badge")?.addEventListener(
      "click",
      () => setInput(shiny, "dashboard_open", Date.now())
    );
    document.addEventListener("click", (ev) => {
      const btn = ev.target.closest(
        '[data-querychat-action="pin-card"]'
      );
      if (!btn) return;
      setInput(shiny, "dashboard_pin", {
        kind: btn.getAttribute("data-kind"),
        title: btn.getAttribute("data-title"),
        source: btn.getAttribute("data-source")
      });
    });
  }
  function initDashboard() {
    if (initialized) return;
    const shiny = window.Shiny;
    if (!shiny) return;
    initialized = true;
    shiny.addCustomMessageHandler(
      `${PREFIX}drawer-toggle`,
      (msg) => toggleDrawer(shiny, msg)
    );
    shiny.addCustomMessageHandler(
      `${PREFIX}card-upsert`,
      (msg) => upsertCard(shiny, msg)
    );
    shiny.addCustomMessageHandler(
      `${PREFIX}card-remove`,
      (msg) => removeCard(shiny, msg)
    );
    shiny.addCustomMessageHandler(
      `${PREFIX}canvas-reset`,
      (msg) => canvasReset(shiny, msg)
    );
    shiny.addCustomMessageHandler(`${PREFIX}layout-apply`, applyLayout);
    shiny.addCustomMessageHandler(
      `${PREFIX}palette`,
      (msg) => updatePalette(shiny, msg)
    );
    shiny.addCustomMessageHandler(`${PREFIX}badge`, updateBadge);
    shiny.addCustomMessageHandler(`${PREFIX}history`, updateHistory);
    shiny.addCustomMessageHandler(`${PREFIX}autogen`, updateAutogen);
    wireStaticControls(shiny);
  }

  // src/dashboard.ts
  initDashboard();
})();
/*! Bundled license information:

gridstack/dist/gridstack.js:
  (*!
   * GridStack 11.5.1
   * https://gridstackjs.com/
   *
   * Copyright (c) 2021-2024  Alain Dumesny
   * see root license https://github.com/gridstack/gridstack.js/tree/master/LICENSE
   *)
*/
