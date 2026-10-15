use std::{collections::{BinaryHeap, HashMap, HashSet, hash_map::DefaultHasher}, env, fs::File, io, ops::ControlFlow, hash::Hasher};
use pgn_reader::{RawTag, Reader, SanPlus, Visitor, Skip};
use serde::Deserialize;
use shakmaty::{Chess, Position, CastlingMode, EnPassantMode, fen::{Fen, Epd}, zobrist::Zobrist128};

#[derive(Deserialize)]
struct Target { position_id: usize, fen: String, previous_fen: String, move_uci: String }
#[derive(Deserialize)]
struct TargetGame { game_id: String, moves_uci: String, white: String, black: String }
struct GameSignature { game_id: String, positions: HashSet<usize>, plies: usize, endpoint: usize }
#[derive(Default)]
struct Tags { date: String, white: String, black: String, event: String, fen: String,
    variant: String, source: String, site: String, mode: String, white_elo: u16, black_elo: u16 }
struct Game { tags: Tags, board: Chess, hits: HashSet<usize>, plies: usize,
    moves: Vec<shakmaty::Move>, sequence: DefaultHasher }
struct Indexer { targets: HashMap<Zobrist128, (usize, String)>, edges: HashMap<(Zobrist128, shakmaty::Move), usize>,
    championship_pairs: HashSet<(String, String)> }

fn player(name: &str) -> String {
    let surname = name.split(',').next().unwrap().split_whitespace().next().unwrap_or("");
    let key: String = surname.to_lowercase().chars().filter(|c| c.is_ascii_alphabetic()).collect();
    match key.as_str() { "kortschnoj" | "kortchnoi" => "korchnoi".into(),
        "spasski" => "spassky".into(), "gukeshd" => "gukesh".into(), _ => key }
}
impl Visitor for Indexer {
    type Tags = Tags;
    type Movetext = Game;
    type Output = Result<Game, String>;
    fn begin_tags(&mut self) -> ControlFlow<Self::Output, Tags> { ControlFlow::Continue(Tags::default()) }
    fn tag(&mut self, tags: &mut Tags, name: &[u8], value: RawTag<'_>) -> ControlFlow<Self::Output> {
        let value = value.decode_utf8_lossy().into_owned();
        match name {
            b"Date" => tags.date = value, b"White" => tags.white = value,
            b"Black" => tags.black = value, b"Event" => tags.event = value,
            b"FEN" => tags.fen = value, b"Variant" => tags.variant = value,
            b"Source" => tags.source = value,
            b"Site" => tags.site = value, b"Mode" => tags.mode = value,
            b"WhiteElo" => tags.white_elo = value.parse().unwrap_or(0),
            b"BlackElo" => tags.black_elo = value.parse().unwrap_or(0), _ => ()
        }
        ControlFlow::Continue(())
    }
    fn begin_movetext(&mut self, tags: Tags) -> ControlFlow<Self::Output, Game> {
        let context = format!("{} {} {}", tags.event, tags.site, tags.mode).to_lowercase();
        let correspondence = context.split(|c: char| !c.is_alphanumeric()).any(|word|
            ["corr", "correspondence", "iccf", "email", "iecc", "iecg"].contains(&word));
        let online = ["online", "internet", "chess.com", "lichess.org", "chess24.com",
            "pro chess league", "meltwater", "magnus carlsen invitational", "chessable masters",
            "aimchess rapid", "opera euro rapid", "new in chess classic", "goldmoney asian rapid"]
            .iter().any(|word| context.contains(word));
        if correspondence || online {
            return ControlFlow::Break(Err(format!("excluded non-OTB metadata: {} {} {} {}", tags.date,
                tags.white, tags.black, context)));
        }
        if !tags.fen.is_empty() || (!tags.variant.is_empty() && tags.variant != "Standard") {
            return ControlFlow::Break(Err(format!("nonstandard start: {} {} {}", tags.date, tags.white, tags.black)));
        }
        ControlFlow::Continue(Game { tags, board: Chess::default(), hits: HashSet::new(), plies: 0,
            moves: Vec::new(), sequence: DefaultHasher::new() })
    }
    fn san(&mut self, game: &mut Game, san: SanPlus) -> ControlFlow<Self::Output> {
        let previous = game.board.zobrist_hash::<Zobrist128>(EnPassantMode::Legal);
        let m = match san.san.to_move(&game.board) {
            Ok(m) => m,
            Err(e) => return ControlFlow::Break(Err(format!("{} {} {} ply {}: {} ({})", game.tags.date,
                game.tags.white, game.tags.black, game.plies + 1, san, e)))
        };
        game.board.play_unchecked(m);
        if let Some(id) = self.edges.get(&(previous, m)) { game.hits.insert(*id); }
        game.moves.push(m);
        game.plies += 1;
        let hash = game.board.zobrist_hash::<Zobrist128>(EnPassantMode::Legal);
        game.sequence.write_u128(hash.0);
        if let Some((id, fen)) = self.targets.get(&hash) {
            // check the full position before accepting a hash match
            assert_eq!(&Epd::from_position(&game.board, EnPassantMode::Legal).to_string(), fen);
            game.hits.insert(*id);
        }
        ControlFlow::Continue(())
    }
    fn begin_variation(&mut self, _: &mut Game) -> ControlFlow<Self::Output, Skip> {
        ControlFlow::Continue(Skip(true))
    }
    fn end_game(&mut self, game: Game) -> Self::Output { Ok(game) }
}

fn date_end(date: &str) -> Option<(u16, String)> {
    let parts: Vec<_> = date.split('.').collect();
    if parts.len() != 3 { return None; }
    let year: u16 = parts[0].parse().ok()?;
    if year == 0 || year > 2024 { return None; }
    let month = if parts[1] == "??" { 12 } else { parts[1].parse::<u8>().ok()? };
    if month == 0 || month > 12 { return None; }
    let max_day = match month { 2 => if year % 4 == 0 && (year % 100 != 0 || year % 400 == 0) {29} else {28},
        4 | 6 | 9 | 11 => 30, _ => 31 };
    let day = if parts[2] == "??" { max_day } else { parts[2].parse::<u8>().ok()? };
    if day == 0 || day > max_day || (parts[1] == "??" && parts[2] != "??") { return None; }
    Some((year, format!("{year:04}{month:02}{day:02}")))
}

struct Witness { count: u64, rated_count: u64, date_end: String, date: String, ordinal: usize,
    white: String, black: String, event: String, source: String,
    rated_date_end: String, rated_ordinal: usize }
#[derive(Eq, PartialEq, Ord, PartialOrd)]
struct Sample { priority: u64, ordinal: usize, positions: Vec<usize> }
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    assert_eq!(args.len(), 4, "master-index TARGETS.csv TARGET_GAMES.csv OUTPUT_PREFIX < batch.pgn");
    let mut targets = HashMap::new();
    let mut edges = HashMap::new();
    for row in csv::Reader::from_path(&args[1])?.deserialize::<Target>() {
        let row = row?;
        if row.previous_fen.is_empty() {
            let board: Chess = Fen::from_ascii(row.fen.as_bytes())?.into_position(CastlingMode::Standard)?;
            let hash = board.zobrist_hash::<Zobrist128>(EnPassantMode::Legal);
            assert!(targets.insert(hash, (row.position_id, Epd::from_position(&board, EnPassantMode::Legal).to_string())).is_none());
        } else {
            let board: Chess = Fen::from_ascii(row.previous_fen.as_bytes())?.into_position(CastlingMode::Standard)?;
            let m = row.move_uci.parse::<shakmaty::uci::UciMove>()?.to_move(&board)?;
            assert!(edges.insert((board.zobrist_hash(EnPassantMode::Legal), m), row.position_id).is_none());
        }
    }
    let mut indexer = Indexer { targets, edges, championship_pairs: HashSet::new() };
    let mut target_games: HashMap<u64, Vec<TargetGame>> = HashMap::new();
    let mut signatures: HashMap<(String, String), Vec<GameSignature>> = HashMap::new();
    for row in csv::Reader::from_path(&args[2])?.deserialize::<TargetGame>() {
        let row = row?;
        let pair = (player(&row.white), player(&row.black));
        indexer.championship_pairs.insert(pair.clone());
        indexer.championship_pairs.insert((pair.1.clone(), pair.0.clone()));
        let mut board = Chess::default();
        let mut sequence = DefaultHasher::new();
        let mut positions = HashSet::new();
        let mut endpoint = 0;
        let mut plies = 0;
        for uci in row.moves_uci.split_whitespace() {
            let m = uci.parse::<shakmaty::uci::UciMove>()?.to_move(&board)?;
            board.play_unchecked(m);
            let hash = board.zobrist_hash::<Zobrist128>(EnPassantMode::Legal);
            sequence.write_u128(hash.0);
            endpoint = indexer.targets[&hash].0;
            positions.insert(endpoint);
            plies += 1;
        }
        signatures.entry(pair).or_default().push(GameSignature { game_id: row.game_id.clone(), positions, plies, endpoint });
        target_games.entry(sequence.finish()).or_default().push(row);
    }
    let mut matches = csv::Writer::from_path(format!("{}.matches.csv", args[3]))?;
    matches.write_record(["game_id", "source_ordinal", "date", "white", "black", "event", "source"])?;
    let mut excluded_scores = csv::Writer::from_path(format!("{}.excluded.csv", args[3]))?;
    excluded_scores.write_record(["source_ordinal", "date", "white", "black", "event", "reason", "target_game_id"])?;
    let mut reader = Reader::new(io::stdin().lock());
    let mut index: HashMap<(usize, u16), Witness> = HashMap::new();
    let mut years: HashMap<u16, (u64, u64)> = HashMap::new();
    let mut samples: HashMap<u16, BinaryHeap<Sample>> = HashMap::new();
    let (mut games, mut valid, mut undated, mut empty, mut excluded, mut excluded_target_count, mut excluded_titles, mut near_copies) = (0, 0, 0, 0, 0, 0, 0, 0);
    let mut errors = csv::Writer::from_path(format!("{}.errors.csv", args[3]))?;
    errors.write_record(["source_ordinal", "reason"])?;
    while let Some(result) = reader.read_game(&mut indexer)? {
        games += 1;
        let game = match result { Ok(game) => game, Err(e) => {
            if e.starts_with("excluded non-OTB") { excluded += 1; }
            errors.write_record([games.to_string(), e])?; continue;
        }};
        valid += 1;
        let pair = (player(&game.tags.white), player(&game.tags.black));
        let mut copied_target = None;
        if let Some(candidates) = target_games.get(&game.sequence.finish()) {
            let uci = game.moves.iter().map(|m| m.to_uci(CastlingMode::Standard).to_string()).collect::<Vec<_>>().join(" ");
            for candidate in candidates {
                assert_eq!(candidate.moves_uci, uci);
                if game.plies >= 40 || pair == (player(&candidate.white), player(&candidate.black)) {
                    copied_target = Some(candidate.game_id.clone());
                }
                matches.write_record([candidate.game_id.clone(), games.to_string(), game.tags.date.clone(),
                    game.tags.white.clone(), game.tags.black.clone(), game.tags.event.clone(), game.tags.source.clone()])?;
            }
        }
        let event = game.tags.event.to_lowercase();
        let mut reason = "";
        if indexer.championship_pairs.contains(&pair) &&
            ["wch", "wcc", "world-ch", "world ch"].iter().any(|word| event.contains(word)) {
            excluded_titles += 1; reason = "championship event and players";
        } else if copied_target.is_some() {
            excluded_target_count += 1; reason = "identical complete score";
        } else if let Some(candidates) = signatures.get(&pair) {
            // quarantine close score variants; short book draws can be independent games
            for candidate in candidates {
                if candidate.plies >= 40 && game.hits.contains(&candidate.endpoint) &&
                    game.plies.abs_diff(candidate.plies) <= 4.max(candidate.plies / 10) &&
                    game.hits.intersection(&candidate.positions).count() * 10 >= candidate.positions.len() * 7 {
                    near_copies += 1; reason = "same players and terminal position; at least 70% of positions shared";
                    copied_target = Some(candidate.game_id.clone()); break;
                }
            }
        }
        if !reason.is_empty() {
            excluded_scores.write_record([games.to_string(), game.tags.date.clone(), game.tags.white.clone(),
                game.tags.black.clone(), game.tags.event.clone(), reason.into(), copied_target.unwrap_or_default()])?;
            continue;
        }
        if game.plies == 0 { empty += 1; continue; }
        let Some((year, end)) = date_end(&game.tags.date) else { undated += 1; continue; };
        let rated = game.tags.white_elo >= 2200 && game.tags.black_elo >= 2200;
        let count = years.entry(year).or_default(); count.0 += 1; count.1 += u64::from(rated);
        // annual bottom-k samples contain the bottom-k of every earlier-year union
        let mut priority = DefaultHasher::new();
        priority.write(args[3].as_bytes()); priority.write_usize(games);
        let priority = priority.finish();
        let pool = samples.entry(year).or_default();
        if pool.len() < 10_000 || priority < pool.peek().unwrap().priority {
            let mut positions: Vec<_> = game.hits.iter().copied().collect(); positions.sort_unstable();
            pool.push(Sample { priority, ordinal: games, positions });
            if pool.len() > 10_000 { pool.pop(); }
        }
        // commit hits only after the entire main line has parsed legally
        for id in game.hits {
            let witness = index.entry((id, year)).or_insert_with(|| Witness {
                count: 0, rated_count: 0, date_end: end.clone(), date: game.tags.date.clone(), ordinal: games,
                white: game.tags.white.clone(), black: game.tags.black.clone(), event: game.tags.event.clone(),
                source: game.tags.source.clone(), rated_date_end: String::new(), rated_ordinal: 0 });
            witness.count += 1;
            if end < witness.date_end {
                witness.date_end = end.clone(); witness.date = game.tags.date.clone(); witness.ordinal = games;
                witness.white = game.tags.white.clone(); witness.black = game.tags.black.clone();
                witness.event = game.tags.event.clone(); witness.source = game.tags.source.clone();
            }
            if rated {
                witness.rated_count += 1;
                if witness.rated_date_end.is_empty() || end < witness.rated_date_end {
                    witness.rated_date_end = end.clone(); witness.rated_ordinal = games;
                }
            }
        }
    }
    let mut out = csv::Writer::from_path(format!("{}.positions.csv", args[3]))?;
    out.write_record(["position_id", "year", "games", "both_2200_games", "earliest_date_end", "date", "source_ordinal", "white", "black", "event", "source", "both_2200_date_end", "both_2200_ordinal"])?;
    let mut keys: Vec<_> = index.keys().copied().collect(); keys.sort_unstable();
    for (id, year) in keys {
        let w = &index[&(id, year)];
        out.write_record([id.to_string(), year.to_string(), w.count.to_string(), w.rated_count.to_string(), w.date_end.clone(),
            w.date.clone(), w.ordinal.to_string(), w.white.clone(), w.black.clone(), w.event.clone(), w.source.clone(),
            w.rated_date_end.clone(), w.rated_ordinal.to_string()])?;
    }
    let mut coverage = csv::Writer::from_path(format!("{}.years.csv", args[3]))?;
    coverage.write_record(["year", "games", "both_2200_games"])?;
    let mut sorted_years: Vec<_> = years.keys().copied().collect(); sorted_years.sort_unstable();
    for year in &sorted_years { let (n, rated) = years[year]; coverage.write_record([year.to_string(), n.to_string(), rated.to_string()])?; }
    let mut sampled = csv::Writer::from_path(format!("{}.samples.csv", args[3]))?;
    sampled.write_record(["year", "priority", "source_ordinal", "position_ids"])?;
    let mut sample_count = 0;
    for year in sorted_years {
        for game in samples.remove(&year).unwrap().into_sorted_vec() {
            sampled.write_record([year.to_string(), game.priority.to_string(), game.ordinal.to_string(),
                game.positions.iter().map(|id| id.to_string()).collect::<Vec<_>>().join(" ")])?;
            sample_count += 1;
        }
    }
    let summary = serde_json::json!({"games": games, "valid_mainlines": valid, "rejected_games": games-valid-excluded,
        "excluded_non_otb_metadata": excluded,
        "excluded_championship_copies": excluded_target_count,
        "excluded_championship_metadata": excluded_titles,
        "excluded_near_copies": near_copies,
        "undated_or_outside_period": undated, "empty_games": empty, "target_positions": indexer.targets.len(),
        "target_edges": indexer.edges.len(), "sampled_games": sample_count, "sample_pool_per_year": 10_000});
    serde_json::to_writer_pretty(File::create(format!("{}.json", args[3]))?, &summary)?;
    println!("{}", summary);
    Ok(())
}
