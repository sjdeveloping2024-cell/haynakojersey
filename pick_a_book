-- ============================================================
--  Pick-A-Book Library System  –  MySQL Schema
--  Run this in MySQL Workbench to create the database
-- ============================================================

-- 1. Create & use the database
CREATE DATABASE IF NOT EXISTS pick_a_book
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE pick_a_book;

-- ─── 2. LIBRARIANS ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS librarians (
    id          INT             NOT NULL AUTO_INCREMENT,
    full_name   VARCHAR(100)    NOT NULL,
    email       VARCHAR(150)    NOT NULL UNIQUE,
    password    VARCHAR(255)    NOT NULL,
    role        VARCHAR(30)     NOT NULL DEFAULT 'librarian',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ─── 3. BOOKS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS books (
    id          INT             NOT NULL AUTO_INCREMENT,
    title       VARCHAR(255)    NOT NULL,
    author      VARCHAR(150)    NOT NULL,
    isbn        VARCHAR(50)     NULL,
    category    VARCHAR(100)    NULL,
    quantity    INT             NOT NULL DEFAULT 1,
    available   INT             NOT NULL DEFAULT 1,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ─── 4. STUDENTS ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id          INT             NOT NULL AUTO_INCREMENT,
    student_id  VARCHAR(50)     NOT NULL UNIQUE,
    full_name   VARCHAR(100)    NOT NULL,
    email       VARCHAR(150)    NULL,
    course      VARCHAR(100)    NULL,
    year_level  TINYINT         NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- ─── 5. BORROWS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS borrows (
    id          INT             NOT NULL AUTO_INCREMENT,
    student_id  INT             NOT NULL,
    book_id     INT             NOT NULL,
    borrow_date DATE            NOT NULL DEFAULT (CURRENT_DATE),
    due_date    DATE            NULL,
    return_date DATE            NULL,
    status      ENUM('borrowed','returned') NOT NULL DEFAULT 'borrowed',
    PRIMARY KEY (id),
    CONSTRAINT fk_borrow_student
        FOREIGN KEY (student_id) REFERENCES students (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_borrow_book
        FOREIGN KEY (book_id) REFERENCES books (id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- ─── 6. INDEXES ─────────────────────────────────────────────
CREATE INDEX idx_borrows_status      ON borrows  (status);
CREATE INDEX idx_borrows_student     ON borrows  (student_id);
CREATE INDEX idx_borrows_book        ON borrows  (book_id);
CREATE INDEX idx_students_student_id ON students (student_id);
CREATE INDEX idx_books_title         ON books    (title);

-- ─── 7. SAMPLE SEED DATA (optional – delete if not needed) ──
INSERT INTO librarians (full_name, email, password, role) VALUES
    ('Admin Librarian', 'admin@pickabook.com', 'admin123', 'admin');

INSERT INTO books (title, author, isbn, category, quantity, available) VALUES
    ('The Great Gatsby',          'F. Scott Fitzgerald', '9780743273565', 'Fiction',       3, 3),
    ('To Kill a Mockingbird',     'Harper Lee',          '9780061935466', 'Fiction',       2, 2),
    ('Introduction to Algorithms','Thomas H. Cormen',    '9780262033848', 'Computer Science', 2, 2),
    ('Clean Code',                'Robert C. Martin',    '9780132350884', 'Computer Science', 1, 1),
    ('1984',                      'George Orwell',       '9780451524935', 'Fiction',       4, 4);

INSERT INTO students (student_id, full_name, email, course, year_level) VALUES
    ('2024-0001', 'Juan dela Cruz',  'juan@school.edu', 'BSIT',  2),
    ('2024-0002', 'Maria Santos',    'maria@school.edu','BSCS',  3),
    ('2024-0003', 'Pedro Reyes',     'pedro@school.edu','BSBA',  1);
