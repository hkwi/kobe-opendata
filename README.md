About
=====
[神戸市オープンデータ](http://www.city.kobe.lg.jp/information/opendata/index.html)を加工するプロジェクトです。[Code for kobe](https://github.com/codeforkobe/) です。

github で直接公開されているデータもあります https://github.com/City-of-Kobe/opendata

各ファイルのライセンスは、神戸市オープンデータの[元データのライセンス](http://www.city.kobe.lg.jp/information/opendata/catalogue.html)をそれぞれ継承します。


神戸市広報紙
------------
神戸市広報紙の HTML コンテンツを変換して RSS + iCalendar のデータとして使えるようにしています。

RSS の URL はこちらです。Thunderbird などに登録することができます。
https://hkwi.github.io/kobe-opendata/refine/kouhoushi/index.xml

補足：紙媒体では例えば2016年5月版では、中央区だと次のように3つが合体している。
- 神戸市広報 13 ページ
- 反対側から中央区区民広報紙 3 ページ
- 間に神戸市会だよりが 4 ページが折込で挟んである

神戸市広報については PDF 版は 8 ページ目まで用意されている。
そのあとのページはテキストで html で掲載されている。

中央区広報は、区のページに PDF が用意されている。
http://www.city.kobe.lg.jp/ward/kuyakusho/chuou/

市会だよりも PDF が用意されている。
http://www.city.kobe.lg.jp/information/municipal/kouhou/tayori/tayori.html


神戸市営地下鉄GTFS
------------------
時刻表を [GTFS](https://developers.google.com/transit/gtfs/) 形式に変換しています。

URL はこちらです。
https://hkwi.github.io/kobe-opendata/refine/subway.zip


ディレクトリ構成
----------------
import
* catalog.py はオープンデータ一覧ページの変更を追跡するプログラムです。
* import ディレクトリは、神戸市 web サイトで公開されているオープンデータの取り込みを行っています。
* catalog-download.csv と catalog-publish.csv に変更がある場合、import の調整が必要です。

refine
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
http://www.ssl.city.kobe.lg.jp/map/shisetsumap.html のデータ相当のようです。
「カテゴリリスト」で種類別に分割すると元のファイルに戻ります。

rdf
* Linked opendata として使える語彙を使って整備したい。
整備するにあたっては、具体的にどのデータセットとの結合ができるようにするかを仮定しないと始まらなさそう。
* import/stat/* は、http://www.statld.org/ を参考にしつつ
[qb namespace](http://www.w3.org/TR/vocab-data-cube/) を使って対応していきたい。
* sculpture* は他の芸術作品用のデータベースとの結合があるだろう。引き続き結合先の候補を探す。
https://yorkdl.wordpress.com/category/openart/

