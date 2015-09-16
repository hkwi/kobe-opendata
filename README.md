About
-----
[神戸市オープンデータ](http://www.city.kobe.lg.jp/information/opendata/index.html)を加工するプロジェクトです。

github で直接公開されているデータもあります https://github.com/City-of-Kobe/opendata

各ファイルのライセンスは、神戸市オープンデータの[元データのライセンス](http://www.city.kobe.lg.jp/information/opendata/catalogue.html)をそれぞれ継承します。


import
------
* catalog.py はオープンデータ一覧ページの変更を追跡するプログラムです。
* import ディレクトリは、神戸市 web サイトで公開されているオープンデータの取り込みを行っています。
* catalog-download.csv と catalog-publish.csv に変更がある場合、import の調整が必要です。

refine
------
* 直接的にデータを使うのに適したフォーマット変換を行います。
* 目標
  * import からの自動変換
  * 変換ルールは手動対応
  * UTF-8 BOM 無し
  * データのcleanup
  * 高度なライブラリ無しで使える形式
  * 値に改行を含まない
* つまり
  * 無理に rdf にしない
  * linked data にするところはスコープ外

import/catalog/institution* は、形式が同じなので 1 ファイルにまとめます。
「カテゴリリスト」で種類別に分割すると元のファイルに戻ります。


rdf
---
Linked opendata として使える語彙を使って整備したい。整備するにあたっては、具体的にどのデータセットとの結合ができるようにするかを仮定しないと始まらなさそう。

import/stat/* は、http://www.statld.org/ を参考にしつつ [qb namespace](http://www.w3.org/TR/vocab-data-cube/) を使って対応していきたい。

https://yorkdl.wordpress.com/category/openart/
