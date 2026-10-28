export function spotifyArtistId(url) {
  const match = /open\.spotify\.com\/artist\/([A-Za-z0-9]+)/.exec(url || "");
  return match ? match[1] : null;
}

export default function SpotifyPlayer({ id, name }) {
  return (
    <iframe
      className="spotify"
      src={`https://open.spotify.com/embed/artist/${id}?theme=0`}
      height="152"
      loading="lazy"
      title={`${name} on Spotify`}
      allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
    />
  );
}
