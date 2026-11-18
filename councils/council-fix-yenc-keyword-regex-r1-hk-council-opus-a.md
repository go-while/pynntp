# fix/yenc-keyword-regex (54751e2) — hk-council-opus-a
Score: 9

No findings. The lookbehind does not change which keys match: the leftmost match already started at a word start ('x-name=' still gives 'name', and 'a=b=c' still gives a:'b=c'). It removes the quadratic retries inside a long word. Not verified on a host.
