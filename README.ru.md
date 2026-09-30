![RAG Change Inspector](assets/preview.png)

# RAG Change Inspector

**Увидь, где поиск стал хуже.**

Сравни два снимка выдачи, найди потерянные источники и изменившиеся фрагменты. Исследуй результат в одном автономном HTML-файле.

[English](README.md) · [Документация](docs/usage.md) · [MIT](LICENSE)

## Попробовать

Python 3.11+. Выполни из папки репозитория; для ядра не нужны внешние зависимости.

```shell
python -m rag_change_inspector init rag-demo
python -m rag_change_inspector compare rag-demo/before.json rag-demo/after.json --k 1 --html reports/diff.html
```

## Что внутри

Четыре метрики, изменения рангов и текста, фильтр регрессий, поиск по отчёту, проверки CI и Chroma-адаптер.

## Границы

Нужны стабильные ID и одинаковая разметка. Пример намеренно возвращает код 1. Отчёт показывает изменения, но не доказывает их причину. Ранний релиз: API может меняться.

Автор: [Алексей Марышев / MOHAPX-V-IT](https://mohapx-v-it.github.io/mohapx-v-iti/).
