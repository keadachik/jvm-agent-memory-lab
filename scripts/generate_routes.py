#!/usr/bin/env python3
"""
RouteController.java を生成する。

route1..routeN を「実際に別々のメソッド」として書き出す(パスパラメータで分岐する
実装だと同一コードパス扱いになり、エージェントのコードレベル計測上「別メソッド」と
認識されない可能性が高いため)。各メソッド本体にはその番号をリテラルで埋め込み、
テキスト的にも別メソッドになるようにする。

さらに route0 を「予備ルート」として1本追加する。これは Step B (カバレッジテスト)
では絶対に呼ばず、Step D (ロングテール検証) で初めて呼ぶために予約しておくもの。

Usage: python3 generate_routes.py [N] > ../java-app/src/main/java/com/example/memlab/RouteController.java
"""
import sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200

HEADER = """package com.example.memlab;

import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 自動生成ファイル。scripts/generate_routes.py で生成する。手編集しないこと。
 *
 * route1..routeN は「累積コードパス数」を制御するための独立したエンドポイント。
 * route0 は Step D (ロングテール検証) 用の予備ルートで、Step B では呼ばないこと。
 */
@RestController
public class RouteController {

"""

FOOTER = "}\n"

METHOD_TEMPLATE = """    @GetMapping("/route/{n}")
    public Map<String, Object> route{n}() {{
        String id = UUID.randomUUID().toString();
        long seed = {n}L * 31L + id.hashCode();
        return Map.of("route", {n}, "id", id, "seed", seed);
    }}

"""

def main():
    parts = [HEADER]
    # route0: 予備ルート(ロングテール検証用)
    parts.append(METHOD_TEMPLATE.format(n=0))
    for i in range(1, N + 1):
        parts.append(METHOD_TEMPLATE.format(n=i))
    parts.append(FOOTER)
    sys.stdout.write("".join(parts))

if __name__ == "__main__":
    main()
