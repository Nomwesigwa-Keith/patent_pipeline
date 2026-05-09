-- Q1: Top Inventors
SELECT i.name, COUNT(DISTINCT r.patent_id) AS patent_count
FROM inventors i
    JOIN relationships r ON i.inventor_id = r.inventor_id
WHERE
    r.inventor_id IS NOT NULL
GROUP BY
    i.inventor_id
ORDER BY patent_count DESC
LIMIT 10;

-- Q2: Top Companies
SELECT c.name, COUNT(DISTINCT r.patent_id) AS patent_count
FROM companies c
    JOIN relationships r ON c.company_id = r.company_id
WHERE
    r.company_id IS NOT NULL
GROUP BY
    c.company_id
ORDER BY patent_count DESC
LIMIT 10;

-- Q3: Countries
SELECT i.country, COUNT(DISTINCT r.patent_id) AS patent_count
FROM inventors i
    JOIN relationships r ON i.inventor_id = r.inventor_id
WHERE
    i.country IS NOT NULL
    AND r.inventor_id IS NOT NULL
GROUP BY
    i.country
ORDER BY patent_count DESC
LIMIT 10;

-- Q4: Trends Over Time
SELECT year, COUNT(patent_id) AS patent_count
FROM patents
WHERE
    year IS NOT NULL
GROUP BY
    year
ORDER BY year ASC;

-- Q5: JOIN Query - combine patents with inventors and companies
WITH
    inventor_links AS (
        SELECT patent_id, inventor_id
        FROM relationships
        WHERE
            inventor_id IS NOT NULL
    ),
    company_links AS (
        SELECT patent_id, company_id
        FROM relationships
        WHERE
            company_id IS NOT NULL
    )
SELECT
    p.patent_id,
    p.title,
    p.year,
    i.name AS inventor_name,
    c.name AS company_name
FROM
    patents p
    JOIN inventor_links il ON p.patent_id = il.patent_id
    JOIN inventors i ON il.inventor_id = i.inventor_id
    LEFT JOIN company_links cl ON p.patent_id = cl.patent_id
    LEFT JOIN companies c ON cl.company_id = c.company_id
LIMIT 20;

-- Q6: CTE Query (WITH statement)
WITH
    inventor_totals AS (
        SELECT i.inventor_id, i.name, i.country, COUNT(DISTINCT r.patent_id) AS total_patents
        FROM inventors i
            JOIN relationships r ON i.inventor_id = r.inventor_id
        WHERE
            r.inventor_id IS NOT NULL
        GROUP BY
            i.inventor_id
    )
SELECT name, country, total_patents
FROM inventor_totals
WHERE
    total_patents > 50
ORDER BY total_patents DESC
LIMIT 10;

-- Q7: Ranking Query using window function
WITH
    inventor_counts AS (
        SELECT i.inventor_id, i.name, i.country, COUNT(DISTINCT r.patent_id) AS patent_count
        FROM inventors i
            JOIN relationships r ON i.inventor_id = r.inventor_id
        WHERE
            r.inventor_id IS NOT NULL
        GROUP BY
            i.inventor_id
    ),
    ranked AS (
        SELECT
            name,
            country,
            patent_count,
            RANK() OVER (
                ORDER BY patent_count DESC
            ) AS inventor_rank
        FROM inventor_counts
    )
SELECT
    name,
    country,
    patent_count,
    inventor_rank
FROM ranked
ORDER BY inventor_rank ASC, name ASC
LIMIT 20;