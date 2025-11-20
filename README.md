我发现，目前中文自然语言语料，可用开源书籍资料匮乏，因此开这个仓库用来收集整理版权归公众所有的书籍，供学者和工业生产使用。

To date, there is a lack of open source books available for Chinese natural language processing. The purpose of launching this repository is to collect open copyright Chinese books for use by scholars and industrial production.

[更多说明](docs/使用说明.md) | [MORE ABOUT](docs/usage.md)

---

# Usage Guide / 使用指南

This repository includes tools to import the book collection into a MySQL database for easier analysis and processing.

## Deployment / 部署

### 1. Environment Setup / 环境搭建
It is recommended to use **Conda** to manage the Python environment to ensure a clean and consistent setup.
推荐使用 **Conda** 来管理 Python 环境，以确保环境的整洁和一致性。

#### Create Conda Environment / 创建 Conda 环境
Run the following commands to create and activate a new environment named `shu_env` with Python 3.9:
运行以下命令创建一个名为 `shu_env` 的 Python 3.9 环境并激活：

```bash
conda create -n shu_env python=3.9
conda activate shu_env
```

#### Install Dependencies / 安装依赖
Install the required Python packages using the provided `requirements.txt` file:
使用提供的 `requirements.txt` 文件安装所需的 Python 包：

```bash
pip install -r requirements.txt
```

**Dependencies / 依赖列表:**
- `mysql-connector-python`: For connecting to the MySQL database.

### 2. Configuration / 配置
The database connection settings are currently located in the `config` dictionary within `tools/db_setup.py` and `tools/import_books.py`. Please update them to match your environment:
数据库连接配置位于 `tools/db_setup.py` 和 `tools/import_books.py` 中的 `config` 字典。请根据您的环境更新以下字段：

- `user`: Database user / 数据库用户名
- `password`: Database password / 数据库密码
- `host`: Database host IP / 数据库主机 IP
- `port`: Database port (default 3306) / 数据库端口
- `database`: Database name / 数据库名称

## Steps / 步骤

### 1. Database Setup / 数据库初始化
Run `db_setup.py` to create the `books` and `chapters` tables.
运行 `db_setup.py` 创建 `books` 和 `chapters` 表。

> **Warning**: This script will `DROP` existing `books` and `chapters` tables to ensure a clean schema update.
> **警告**: 此脚本会删除现有的 `books` 和 `chapters` 表，以确保架构更新。

```bash
python tools/db_setup.py
```

### 2. Import Books / 导入书籍
Run `import_books.py` to parse book files from the `books/` directory and metadata from `index.csv`, then populate the database.
运行 `import_books.py` 解析 `books/` 目录下的书籍文件和 `index.csv` 中的元数据，并填充到数据库中。

```bash
python tools/import_books.py
```

**Key Features / 主要功能:**
- **Smart Chapter Splitting / 智能章节分割**: Automatically handles various chapter formats (e.g., "第X回", "卷X", "Title(Num)", and Table of Contents based splitting for anthologies like "朝花夕拾").
- **Metadata Enrichment / 元数据丰富**: Links books with metadata from `index.csv` (Title, Author, Publication Date, Copyright Year, Last Modified).
- **Content Analysis / 内容分析**: Calculates and stores the character count (`content_length`) for each chapter.
- **Encoding Handling / 编码处理**: Correctly handles UTF-8 BOM in CSV files.

### 3. Verification / 验证
You can use the provided verification scripts to check the integrity of the imported data.
您可以使用提供的验证脚本来检查导入数据的完整性。

```bash
python tools/verify_import.py
```

## Database Schema / 数据库结构

### `books` Table
Stores metadata for each book. / 存储每本书的元数据。
- `id`: Primary Key
- `filename`: Original filename / 原始文件名
- `title`: Book title (derived from filename) / 书名（源自文件名）
- `book_title`: Official book title (from `index.csv`) / 正式书名
- `author`: Author / 作者
- `publication_date`: Publication date / 出版日期
- `copyright_year`: Copyright year / 版权年份
- `last_modified`: Last modified date / 最后修改日期
- `created_at`: Record creation timestamp / 创建时间

### `chapters` Table
Stores the actual content of the books, split by chapter. / 存储书籍的实际内容，按章节分割。
- `id`: Primary Key
- `book_id`: Foreign Key linking to `books.id` / 外键，关联 `books` 表
- `book_name`: Book title (denormalized for easier querying) / 书名（冗余字段，便于查询）
- `chapter_index`: Sequential index of the chapter / 章节序号
- `title`: Chapter title / 章节标题
- `content`: Full text content of the chapter / 章节全文内容
- `content_length`: Number of characters in the content / 内容字数
